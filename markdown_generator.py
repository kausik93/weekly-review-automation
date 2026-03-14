#!/usr/bin/env python3
"""
Markdown Generator
Generates formatted weekly review markdown files for Obsidian.
"""

from datetime import date
from pathlib import Path
from typing import Dict, Optional


class MarkdownGenerator:
    """Generates weekly review markdown files."""

    def __init__(self, vault_path: str, review_folder: str):
        """
        Initialize markdown generator.

        Args:
            vault_path: Path to Obsidian vault
            review_folder: Relative path to weekly reviews folder within vault
        """
        self.vault_path = Path(vault_path)
        self.review_folder = self.vault_path / review_folder

    def generate_review(
        self,
        start_date: date,
        end_date: date,
        diet_table: str,
        diet_summary: Dict,
        diet_observations: str,
        exercise_summary: str,
        exercise_stats: Dict,
        exercise_observations: str,
        goals_by_domain: Dict,
        domain_reflections: Dict
    ) -> str:
        """
        Generate complete weekly review markdown.

        Args:
            start_date: Start of review week
            end_date: End of review week
            diet_table: Markdown table of diet data
            diet_summary: Diet summary statistics
            diet_observations: User's diet observations
            exercise_summary: Markdown summary of workouts
            exercise_stats: Exercise summary statistics
            exercise_observations: User's exercise observations
            goals_by_domain: Grouped goals by domain
            domain_reflections: User reflections for each domain

        Returns:
            Complete markdown content
        """
        md = []

        # Title (implicit in filename)
        md.append("## Mid-week check-in")
        md.append("- Diet, exercise and also work\n")

        # Diet Review
        md.append("## Diet review\n")
        md.append(diet_table)
        md.append("\n**Summary:**")
        md.append(f"- Days within {diet_summary['calorie_target']} cal target: {diet_summary['days_within_calorie_target']}")
        md.append(f"- Days hitting {diet_summary['protein_target']}g protein: {diet_summary['days_hitting_protein_target']}")
        md.append(f"- Average calories: {diet_summary['average_calories']}")
        md.append(f"- Average protein: {diet_summary['average_protein']}g\n")

        if diet_observations:
            md.append(diet_observations + "\n")

        # Exercise Review
        md.append("## Exercise review\n")
        md.append(exercise_summary)
        md.append("\n**Summary:**")
        md.append(f"- Gym sessions: {exercise_stats['sessions_ratio']} completed")

        if exercise_stats.get('workout_days'):
            days_str = ", ".join([f"{d['day']}" for d in exercise_stats['workout_days']])
            md.append(f"- Workout days: {days_str}")

        md.append("")

        if exercise_observations:
            md.append(exercise_observations + "\n")

        # Goals Review
        md.append("## Goals review\n")

        for domain_name, tasks in goals_by_domain.items():
            # Skip domains with no tasks
            if not tasks['discrete_tasks'] and not tasks['process_goals']:
                continue

            md.append(f"### {domain_name}\n")

            # Discrete tasks
            if tasks['discrete_tasks']:
                md.append("**Discrete Tasks:**")
                for task in tasks['discrete_tasks']:
                    checkbox = "[x]" if task['completed'] else "[ ]"
                    md.append(f"- {checkbox} {task['title']}")
                md.append("")

            # Process goals
            if tasks['process_goals']:
                md.append("**Process Goals:**")
                for goal in tasks['process_goals']:
                    progress = goal.get('user_progress', 'Not tracked')
                    md.append(f"- {goal['title']}: {progress}")
                md.append("")

            # Reflection and focus
            reflection = domain_reflections.get(domain_name, {})

            if reflection.get('reflection'):
                md.append(f"**Reflection:** {reflection['reflection']}\n")

            if reflection.get('next_week_focus'):
                md.append(f"**Next week focus:** {reflection['next_week_focus']}\n")

            md.append("---\n")

        return "\n".join(md)

    def write_review(
        self,
        start_date: date,
        content: str,
        dry_run: bool = False
    ) -> str:
        """
        Write review to Obsidian vault.

        Args:
            start_date: Start date of the review week (used for filename)
            content: Markdown content to write
            dry_run: If True, don't actually write the file

        Returns:
            Path where file was (or would be) written
        """
        # Create filename: "Weekly review YYYY-MM-DD.md"
        filename = f"Weekly review {start_date.strftime('%Y-%m-%d')}.md"
        file_path = self.review_folder / filename

        if dry_run:
            print(f"\n[DRY RUN] Would write to: {file_path}")
            print("\n--- Generated Content ---")
            print(content)
            print("--- End of Content ---\n")
            return str(file_path)

        # Ensure directory exists
        self.review_folder.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return str(file_path)


def prompt_for_input(prompt_text: str, default: str = "") -> str:
    """
    Prompt user for input with optional default.

    Args:
        prompt_text: Text to display to user
        default: Default value if user enters nothing

    Returns:
        User's input or default
    """
    if default:
        prompt_text += f" [{default}]"

    prompt_text += ": "

    user_input = input(prompt_text).strip()

    return user_input if user_input else default


def collect_process_goal_progress(goals_by_domain: Dict) -> None:
    """
    Prompt user for progress on process goals.

    Args:
        goals_by_domain: Dictionary of goals grouped by domain (modified in place)
    """
    print("\n" + "="*80)
    print("PROCESS GOALS PROGRESS")
    print("="*80)

    for domain_name, tasks in goals_by_domain.items():
        if not tasks['process_goals']:
            continue

        print(f"\n{domain_name}:")

        for goal in tasks['process_goals']:
            prompt = f"  {goal['title']} - How many days? (e.g., 5/7)"
            progress = prompt_for_input(prompt, "0/7")
            goal['user_progress'] = progress


def collect_domain_reflections(goals_by_domain: Dict) -> Dict:
    """
    Prompt user for reflections on each domain.

    Args:
        goals_by_domain: Dictionary of goals grouped by domain

    Returns:
        Dictionary of reflections by domain
    """
    print("\n" + "="*80)
    print("DOMAIN REFLECTIONS")
    print("="*80)

    reflections = {}

    for domain_name, tasks in goals_by_domain.items():
        # Skip domains with no tasks
        if not tasks['discrete_tasks'] and not tasks['process_goals']:
            continue

        print(f"\n{domain_name}:")

        reflection = prompt_for_input(
            "  Reflection - What worked? What blocked you? (brief)",
            ""
        )

        next_week = prompt_for_input(
            "  Next week focus (brief)",
            ""
        )

        reflections[domain_name] = {
            'reflection': reflection,
            'next_week_focus': next_week
        }

    return reflections


def collect_additional_observations() -> tuple:
    """
    Prompt user for additional observations on diet and exercise.

    Returns:
        Tuple of (diet_observations, exercise_observations)
    """
    print("\n" + "="*80)
    print("ADDITIONAL OBSERVATIONS")
    print("="*80)

    diet_obs = prompt_for_input("\nAny other observations for diet this week?", "")
    exercise_obs = prompt_for_input("Any other observations for exercise this week?", "")

    return diet_obs, exercise_obs
