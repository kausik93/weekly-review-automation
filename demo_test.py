#!/usr/bin/env python3
"""
Demo test of the weekly review script (without TickTick).
This demonstrates the core functionality.
"""

import sys
from datetime import date
from diet_parser import parse_diet_data
from exercise_parser import parse_exercise_data
from markdown_generator import MarkdownGenerator

def main():
    print("\n" + "="*80)
    print("WEEKLY REVIEW AUTOMATION - DEMO TEST")
    print("="*80)

    # Test with bundled synthetic sample data (see sample_data/)
    print("\n[1/3] Testing diet parser...")
    try:
        diet_table, diet_summary = parse_diet_data(
            'sample_data/diet_sample.csv',
            date(2026, 1, 5),
            date(2026, 1, 11),
            2000,
            100
        )
        print(f"  ✓ Parsed {diet_summary['total_days']} days of diet data")
        print(f"    - Days within calorie target: {diet_summary['days_within_calorie_target']}")
        print(f"    - Days hitting protein target: {diet_summary['days_hitting_protein_target']}")
        print(f"    - Avg calories: {diet_summary['average_calories']}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        sys.exit(1)

    print("\n[2/3] Testing exercise parser...")
    try:
        exercise_summary, exercise_stats = parse_exercise_data(
            'sample_data/workouts_sample.csv',
            date(2026, 1, 5),
            date(2026, 1, 11),
            3
        )
        print(f"  ✓ Found {exercise_stats['total_sessions']} workout sessions")
        print(f"    - Sessions ratio: {exercise_stats['sessions_ratio']}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
        sys.exit(1)

    print("\n[3/3] Testing markdown generator...")
    try:
        # Mock goals data for testing
        goals_by_domain = {
            'Health': {
                'discrete_tasks': [
                    {'title': 'Track meals daily', 'completed': True}
                ],
                'process_goals': [
                    {'title': 'Exercise 3x per week', 'user_progress': '3/3'}
                ]
            }
        }

        domain_reflections = {
            'Health': {
                'reflection': 'Stayed on track most days, one slip on Sunday',
                'next_week_focus': 'Plan meals in advance'
            }
        }

        generator = MarkdownGenerator('/tmp/test-vault', 'reviews')

        markdown = generator.generate_review(
            start_date=date(2025, 10, 13),
            end_date=date(2025, 10, 19),
            diet_table=diet_table,
            diet_summary=diet_summary,
            diet_observations="Struggled on weekend",
            exercise_summary=exercise_summary,
            exercise_stats=exercise_stats,
            exercise_observations="Great workout week!",
            goals_by_domain=goals_by_domain,
            domain_reflections=domain_reflections
        )

        print("  ✓ Generated markdown successfully")
        print(f"    - Total length: {len(markdown)} characters")

        # Show preview
        print("\n" + "="*80)
        print("GENERATED MARKDOWN PREVIEW (first 800 chars)")
        print("="*80)
        print(markdown[:800])
        print("...")
        print("="*80)

    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\n✓ All components working correctly!")
    print("\nTo use with TickTick, set environment variables and run:")
    print("  export TICKTICK_USERNAME='your_email'")
    print("  export TICKTICK_PASSWORD='your_password'")
    print("  python weekly_review.py --netdiary-csv <file> --heavy-csv <file> \\")
    print("         --start-date YYYY-MM-DD --end-date YYYY-MM-DD")
    print()

if __name__ == "__main__":
    main()
