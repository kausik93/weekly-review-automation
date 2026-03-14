#!/usr/bin/env python3
"""
TickTick API Client
Handles authentication and task retrieval from TickTick.
"""

import os
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class TickTickClient:
    """Client for TickTick API."""

    API_BASE_URL = "https://api.ticktick.com/api/v2"
    OPEN_API_BASE_URL = "https://api.ticktick.com/open/v1"

    def __init__(self, username: str, password: str, token_cache_file: Optional[str] = None):
        """
        Initialize TickTick client.

        Args:
            username: TickTick username/email
            password: TickTick password
            token_cache_file: Path to cache authentication token
        """
        self.username = username
        self.password = password
        self.token_cache_file = Path(token_cache_file) if token_cache_file else None
        self.access_token = None
        self.token_expiry = None

    def authenticate(self) -> None:
        """Authenticate with TickTick and get access token."""
        # Try to load cached token first
        if self._load_cached_token():
            return

        # Otherwise, authenticate
        print("Authenticating with TickTick...")

        try:
            # TickTick uses a signin endpoint
            response = requests.post(
                f"{self.API_BASE_URL}/user/signon",
                json={
                    "username": self.username,
                    "password": self.password
                },
                params={"wc": "true", "remember": "true"}
            )

            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('token')

                if not self.access_token:
                    raise ValueError("No token in authentication response")

                # Token typically expires in 30 days, set expiry to 28 days to be safe
                self.token_expiry = datetime.now() + timedelta(days=28)

                # Cache the token
                self._save_token_cache()

                print("✓ Successfully authenticated with TickTick")
            elif response.status_code == 503:
                raise ValueError(
                    f"TickTick API is temporarily unavailable (503 error).\n"
                    f"  This could mean:\n"
                    f"  - TickTick's servers are down for maintenance\n"
                    f"  - The API endpoint has changed\n"
                    f"  - Network connectivity issues\n"
                    f"\n  Try again later or use --skip-ticktick to bypass TickTick integration."
                )
            else:
                raise ValueError(f"Authentication failed: {response.status_code} - {response.text}")

        except requests.RequestException as e:
            raise ConnectionError(f"Failed to connect to TickTick API: {e}")

    def _load_cached_token(self) -> bool:
        """Load cached token if available and valid."""
        if not self.token_cache_file or not self.token_cache_file.exists():
            return False

        try:
            with open(self.token_cache_file, 'r') as f:
                cache = json.load(f)

            # Check if token is still valid
            expiry = datetime.fromisoformat(cache.get('expiry', ''))
            if expiry > datetime.now():
                self.access_token = cache.get('token')
                self.token_expiry = expiry
                print("✓ Using cached TickTick authentication")
                return True
        except (json.JSONDecodeError, ValueError, KeyError):
            # Cache is corrupted or invalid, ignore it
            pass

        return False

    def _save_token_cache(self) -> None:
        """Save token to cache file."""
        if not self.token_cache_file:
            return

        cache = {
            'token': self.access_token,
            'expiry': self.token_expiry.isoformat()
        }

        # Ensure directory exists
        self.token_cache_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.token_cache_file, 'w') as f:
            json.dump(cache, f)

        # Set restrictive permissions (owner read/write only)
        self.token_cache_file.chmod(0o600)

    def get_project_tasks(self, project_id: str) -> List[Dict]:
        """
        Get all tasks from a specific project.

        Args:
            project_id: TickTick project ID

        Returns:
            List of task dictionaries
        """
        if not self.access_token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")

        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}'
            }

            # Get all tasks
            response = requests.get(
                f"{self.API_BASE_URL}/batch/check/0",
                headers=headers
            )

            if response.status_code == 401:
                # Token expired, clear cache and re-authenticate
                if self.token_cache_file and self.token_cache_file.exists():
                    self.token_cache_file.unlink()
                raise RuntimeError("Authentication token expired. Please run again to re-authenticate.")

            if response.status_code != 200:
                raise ValueError(f"Failed to fetch tasks: {response.status_code} - {response.text}")

            data = response.json()

            # Filter tasks by project ID
            all_tasks = data.get('syncTaskBean', {}).get('update', [])
            project_tasks = [
                task for task in all_tasks
                if task.get('projectId') == project_id
            ]

            return project_tasks

        except requests.RequestException as e:
            raise ConnectionError(f"Failed to fetch tasks from TickTick: {e}")

    def group_tasks_by_domain(
        self,
        tasks: List[Dict],
        domains: List[Dict]
    ) -> Dict[str, Dict]:
        """
        Group tasks by domain based on title prefixes.

        Args:
            tasks: List of task dictionaries from TickTick
            domains: List of domain configurations with 'name' and 'prefix'

        Returns:
            Dictionary mapping domain names to categorized tasks
        """
        result = {}

        for domain in domains:
            domain_name = domain['name']
            prefix = domain['prefix']

            result[domain_name] = {
                'discrete_tasks': [],
                'process_goals': []
            }

            # Find tasks matching this domain
            for task in tasks:
                title = task.get('title', '')

                if not title.startswith(prefix):
                    continue

                # Remove prefix from title
                clean_title = title[len(prefix):].strip()

                task_info = {
                    'title': clean_title,
                    'completed': task.get('status') == 2,  # Status 2 = completed
                    'id': task.get('id'),
                    'original_title': title
                }

                # Classify as process goal or discrete task
                if self._is_process_goal(clean_title):
                    result[domain_name]['process_goals'].append(task_info)
                else:
                    result[domain_name]['discrete_tasks'].append(task_info)

        return result

    @staticmethod
    def _is_process_goal(title: str) -> bool:
        """
        Determine if a task is a process goal vs discrete task.

        Args:
            title: Task title (without domain prefix)

        Returns:
            True if it's a process goal, False if discrete
        """
        # Process goal indicators
        process_keywords = [
            'every week', 'every day', 'daily', 'weekly',
            'x days', 'x/week', 'whenever', 'each week',
            'per week', 'days a week', 'times a week'
        ]

        title_lower = title.lower()

        for keyword in process_keywords:
            if keyword in title_lower:
                return True

        return False


def fetch_goals_from_ticktick(
    username: str,
    password: str,
    project_id: str,
    domains: List[Dict],
    token_cache_file: Optional[str] = None
) -> Dict[str, Dict]:
    """
    Convenience function to fetch and group goals from TickTick.

    Args:
        username: TickTick username
        password: TickTick password
        project_id: Project ID to fetch tasks from
        domains: List of domain configurations
        token_cache_file: Path to cache authentication token

    Returns:
        Dictionary of grouped tasks by domain
    """
    client = TickTickClient(username, password, token_cache_file)
    client.authenticate()

    tasks = client.get_project_tasks(project_id)
    grouped_tasks = client.group_tasks_by_domain(tasks, domains)

    return grouped_tasks
