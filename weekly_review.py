#!/usr/bin/env python3
"""
Weekly Review Automation Script

Automates the weekly review process by:
1. Parsing diet and exercise data from CSV files
2. Pulling monthly goals from TickTick
3. Prompting user for missing process goal data
4. Generating a formatted weekly review in Obsidian

Usage:
    python weekly_review.py \\
        --netdiary-csv ~/Downloads/netdiary.csv \\
        --heavy-csv ~/Downloads/heavy.csv \\
        --start-date 2026-01-05 \\
        --end-date 2026-01-11 \\
        --config config.yaml
"""

import os
import sys
import yaml
import argparse
from datetime import datetime, date
from pathlib import Path
from typing import Dict

# Import our modules
from diet_parser import parse_diet_data
from exercise_parser import parse_exercise_data
from ticktick_client import fetch_goals_from_ticktick
from markdown_generator import (
    MarkdownGenerator,
    collect_process_goal_progress,
    collect_domain_reflections,
    collect_additional_observations
)


def load_config(config_path: str) -> Dict:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to config file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config file: {e}")

    # Validate required fields
    required_fields = [
        ('ticktick', 'monthly_goals_project_id'),
        ('domains',),
        ('targets', 'daily_calorie_max'),
        ('targets', 'daily_protein_min'),
        ('targets', 'weekly_gym_sessions'),
        ('paths', 'obsidian_vault'),
        ('paths', 'weekly_review_folder')
    ]

    for field_path in required_fields:
        current = config
        for key in field_path:
            if key not in current:
                field_str = '.'.join(field_path)
                raise ValueError(f"Missing required config field: {field_str}")
            current = current[key]

    return config


def validate_dates(start_date: date, end_date: date) -> None:
    """
    Validate date range.

    Args:
        start_date: Start date
        end_date: End date

    Raises:
        ValueError: If dates are invalid
    """
    if start_date > end_date:
        raise ValueError("Start date must be before or equal to end date")

    # Warn if range is more than 10 days (likely a mistake)
    if (end_date - start_date).days > 10:
        print(f"⚠ Warning: Date range is {(end_date - start_date).days} days. " +
              "Weekly reviews are typically 7 days.")


def get_ticktick_credentials() -> tuple:
    """
    Get TickTick credentials from environment variables.

    Returns:
        Tuple of (username, password)

    Raises:
        ValueError: If credentials not found
    """
    username = os.environ.get('TICKTICK_USERNAME')
    password = os.environ.get('TICKTICK_PASSWORD')

    if not username or not password:
        raise ValueError(
            "TickTick credentials not found. Please set TICKTICK_USERNAME and " +
            "TICKTICK_PASSWORD environment variables."
        )

    return username, password


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Weekly Review Automation - Generate weekly reviews for Obsidian',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
  python weekly_review.py \\
    --netdiary-csv ~/Downloads/netdiary_export.csv \\
    --heavy-csv ~/Downloads/heavy_export.csv \\
    --start-date 2026-01-05 \\
    --end-date 2026-01-11 \\
    --config config.yaml

Environment Variables:
  TICKTICK_USERNAME - Your TickTick username/email
  TICKTICK_PASSWORD - Your TickTick password
        """
    )

    parser.add_argument(
        '--netdiary-csv',
        required=True,
        help='Path to NetDiary CSV/Excel export'
    )

    parser.add_argument(
        '--heavy-csv',
        required=True,
        help='Path to Heavy exercise CSV export'
    )

    parser.add_argument(
        '--start-date',
        required=True,
        help='Start of review week (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--end-date',
        required=True,
        help='End of review week (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to config file (default: config.yaml)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview output without writing to Obsidian'
    )

    parser.add_argument(
        '--skip-ticktick',
        action='store_true',
        help='Skip TickTick integration (use for testing or if API is down)'
    )

    parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='Skip interactive prompts (use with --skip-ticktick for testing)'
    )

    args = parser.parse_args()

    try:
        # ============================================================
        # STEP 1: Load configuration and validate inputs
        # ============================================================
        print("\n" + "="*80)
        print("WEEKLY REVIEW GENERATOR")
        print("="*80)

        print("\n[1/7] Loading configuration...")
        config = load_config(args.config)

        # Parse dates
        try:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
        except ValueError as e:
            print(f"✗ Error: Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)

        validate_dates(start_date, end_date)

        print(f"  Date range: {start_date} to {end_date}")
        print(f"  Config: {args.config}")

        # ============================================================
        # STEP 2: Parse diet data
        # ============================================================
        print("\n[2/7] Parsing diet data...")

        try:
            diet_table, diet_summary = parse_diet_data(
                args.netdiary_csv,
                start_date,
                end_date,
                config['targets']['daily_calorie_max'],
                config['targets']['daily_protein_min']
            )
            print(f"  ✓ Loaded {diet_summary['total_days']} days of diet data")
        except Exception as e:
            print(f"  ✗ Error parsing diet data: {e}")
            sys.exit(1)

        # ============================================================
        # STEP 3: Parse exercise data
        # ============================================================
        print("\n[3/7] Parsing exercise data...")

        try:
            exercise_summary, exercise_stats = parse_exercise_data(
                args.heavy_csv,
                start_date,
                end_date,
                config['targets']['weekly_gym_sessions']
            )
            print(f"  ✓ Found {exercise_stats['total_sessions']} workout sessions")
        except Exception as e:
            print(f"  ✗ Error parsing exercise data: {e}")
            sys.exit(1)

        # ============================================================
        # STEP 4: Fetch goals from TickTick
        # ============================================================
        print("\n[4/7] Fetching goals from TickTick...")

        if args.skip_ticktick:
            print("  ⚠ Skipping TickTick (--skip-ticktick flag set)")
            print("  → You'll need to manually add goals to the review")

            # Create empty goals structure
            goals_by_domain = {}
            for domain in config['domains']:
                goals_by_domain[domain['name']] = {
                    'discrete_tasks': [],
                    'process_goals': []
                }
        else:
            try:
                username, password = get_ticktick_credentials()

                # Get token cache file path (make it absolute)
                token_cache = config['ticktick'].get('token_cache_file', '.ticktick_token.json')
                if not Path(token_cache).is_absolute():
                    token_cache = str(Path(args.config).parent / token_cache)

                goals_by_domain = fetch_goals_from_ticktick(
                    username,
                    password,
                    config['ticktick']['monthly_goals_project_id'],
                    config['domains'],
                    token_cache
                )

                total_tasks = sum(
                    len(tasks['discrete_tasks']) + len(tasks['process_goals'])
                    for tasks in goals_by_domain.values()
                )
                print(f"  ✓ Loaded {total_tasks} tasks across {len(config['domains'])} domains")

            except Exception as e:
                print(f"  ✗ Error fetching TickTick data: {e}")
                print(f"\n  💡 Tip: Use --skip-ticktick to bypass TickTick and test the rest")
                sys.exit(1)

        # ============================================================
        # STEP 5: Interactive prompts
        # ============================================================
        print("\n[5/7] Collecting user input...")

        if args.non_interactive:
            print("  ⚠ Non-interactive mode: skipping prompts")
            domain_reflections = {}
            diet_obs = ""
            exercise_obs = ""
        else:
            # Process goals progress
            collect_process_goal_progress(goals_by_domain)

            # Domain reflections
            domain_reflections = collect_domain_reflections(goals_by_domain)

            # Additional observations
            diet_obs, exercise_obs = collect_additional_observations()

        # ============================================================
        # STEP 6: Generate markdown
        # ============================================================
        print("\n[6/7] Generating markdown...")

        generator = MarkdownGenerator(
            config['paths']['obsidian_vault'],
            config['paths']['weekly_review_folder']
        )

        markdown_content = generator.generate_review(
            start_date,
            end_date,
            diet_table,
            diet_summary,
            diet_obs,
            exercise_summary,
            exercise_stats,
            exercise_obs,
            goals_by_domain,
            domain_reflections
        )

        print("  ✓ Markdown generated")

        # ============================================================
        # STEP 7: Write to Obsidian
        # ============================================================
        print("\n[7/7] Writing to Obsidian...")

        output_path = generator.write_review(
            start_date,
            markdown_content,
            dry_run=args.dry_run
        )

        if args.dry_run:
            print("\n✓ Dry run complete. No files were written.")
        else:
            print(f"\n✓ Weekly review written to: {output_path}")

        print("\n" + "="*80)
        print("WEEKLY REVIEW COMPLETE!")
        print("="*80 + "\n")

    except KeyboardInterrupt:
        print("\n\n✗ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
