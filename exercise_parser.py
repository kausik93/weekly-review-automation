#!/usr/bin/env python3
"""
Exercise Data Parser
Parses Heavy/Hevy CSV exports and generates weekly workout summaries.
"""

import pandas as pd
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Tuple


class ExerciseParser:
    """Parser for Heavy/Hevy workout data."""

    def __init__(self, file_path: str):
        """
        Initialize exercise parser.

        Args:
            file_path: Path to Heavy/Hevy CSV file
        """
        self.file_path = Path(file_path)
        self.df = None

    def load_data(self) -> None:
        """Load and prepare Heavy/Hevy data."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"Exercise file not found: {self.file_path}")

        try:
            self.df = pd.read_csv(self.file_path)
        except Exception as e:
            raise ValueError(f"Failed to load exercise data: {e}")

        # Validate required columns
        required_cols = ['title', 'start_time']
        missing_cols = [col for col in required_cols if col not in self.df.columns]
        if missing_cols:
            raise ValueError(f"Exercise file missing required columns: {missing_cols}")

        # Parse dates
        try:
            self.df['start_datetime'] = pd.to_datetime(self.df['start_time'], format='%d %b %Y, %H:%M')
            self.df['workout_date'] = self.df['start_datetime'].dt.date

            if 'end_time' in self.df.columns:
                self.df['end_datetime'] = pd.to_datetime(self.df['end_time'], format='%d %b %Y, %H:%M')
        except Exception as e:
            raise ValueError(f"Failed to parse workout dates: {e}")

    def get_weekly_summary(
        self,
        start_date: date,
        end_date: date,
        weekly_target: int
    ) -> Dict:
        """
        Get workout summary for a date range.

        Args:
            start_date: Start of the week
            end_date: End of the week
            weekly_target: Target number of workouts per week

        Returns:
            Dictionary with workout data and summary stats
        """
        if self.df is None:
            raise RuntimeError("Data not loaded. Call load_data() first.")

        # Filter to date range
        mask = (self.df['workout_date'] >= start_date) & (self.df['workout_date'] <= end_date)
        week_data = self.df[mask].copy()

        if week_data.empty:
            return {
                'workouts': [],
                'summary': {
                    'total_sessions': 0,
                    'target_sessions': weekly_target,
                    'sessions_ratio': f"0/{weekly_target}",
                    'workout_days': []
                }
            }

        # Group by unique workout sessions (title + start_time)
        workouts = []
        workout_days = set()

        for (workout_date, title, start_time), group in week_data.groupby(
            ['workout_date', 'title', 'start_time']
        ):
            workout_days.add(workout_date)

            # Calculate duration if end_time is available
            duration = None
            if 'end_datetime' in self.df.columns:
                start_dt = group['start_datetime'].iloc[0]
                end_dt = group['end_datetime'].iloc[0]
                duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
                duration = self._format_duration(duration_minutes)

            # Get exercise count
            exercise_count = group['exercise_title'].nunique() if 'exercise_title' in group.columns else 0

            workouts.append({
                'date': workout_date,
                'day': datetime.combine(workout_date, datetime.min.time()).strftime('%A'),
                'title': title,
                'duration': duration,
                'exercise_count': exercise_count
            })

        # Sort workouts by date
        workouts.sort(key=lambda x: x['date'])

        # Calculate summary
        total_sessions = len(workouts)
        workout_days_list = sorted(workout_days)

        return {
            'workouts': workouts,
            'summary': {
                'total_sessions': total_sessions,
                'target_sessions': weekly_target,
                'sessions_ratio': f"{total_sessions}/{weekly_target}",
                'workout_days': [
                    {
                        'date': d,
                        'day': datetime.combine(d, datetime.min.time()).strftime('%A')
                    }
                    for d in workout_days_list
                ]
            }
        }

    def generate_markdown_summary(self, workouts: List[Dict]) -> str:
        """
        Generate markdown summary for workout data.

        Args:
            workouts: List of workout dictionaries

        Returns:
            Markdown formatted summary
        """
        if not workouts:
            return "*No workouts found for this period*\n"

        markdown = ""
        for workout in workouts:
            date_str = workout['date'].strftime('%b %d, %Y')
            day = workout['day']
            title = workout['title']

            line = f"- **{date_str} ({day})**: {title}"

            if workout['duration']:
                line += f" - {workout['duration']}"

            if workout['exercise_count'] > 0:
                line += f" ({workout['exercise_count']} exercises)"

            markdown += line + "\n"

        return markdown

    @staticmethod
    def _format_duration(minutes: int) -> str:
        """Format duration in minutes to readable format."""
        if minutes < 60:
            return f"{minutes} mins"
        else:
            hours = minutes // 60
            remaining_mins = minutes % 60
            if remaining_mins == 0:
                return f"{hours} hr" if hours == 1 else f"{hours} hrs"
            else:
                hr_text = "hr" if hours == 1 else "hrs"
                return f"{hours} {hr_text} {remaining_mins} mins"


def parse_exercise_data(
    file_path: str,
    start_date: date,
    end_date: date,
    weekly_target: int
) -> Tuple[str, Dict]:
    """
    Convenience function to parse exercise data and generate output.

    Args:
        file_path: Path to exercise data file
        start_date: Start of the week
        end_date: End of the week
        weekly_target: Target number of workouts per week

    Returns:
        Tuple of (markdown_summary, summary_dict)
    """
    parser = ExerciseParser(file_path)
    parser.load_data()

    result = parser.get_weekly_summary(start_date, end_date, weekly_target)

    markdown_summary = parser.generate_markdown_summary(result['workouts'])

    return markdown_summary, result['summary']
