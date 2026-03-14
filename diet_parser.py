#!/usr/bin/env python3
"""
Diet Data Parser
Parses NetDiary CSV/Excel exports and generates weekly summaries.
"""

import pandas as pd
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Tuple


class DietParser:
    """Parser for NetDiary diet data."""

    def __init__(self, file_path: str):
        """
        Initialize diet parser.

        Args:
            file_path: Path to NetDiary CSV or Excel file
        """
        self.file_path = Path(file_path)
        self.df = None

    def load_data(self) -> None:
        """Load and prepare NetDiary data."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"Diet file not found: {self.file_path}")

        # Try Excel first, then CSV
        try:
            if self.file_path.suffix.lower() in ['.xls', '.xlsx']:
                self.df = pd.read_excel(self.file_path)
            else:
                self.df = pd.read_csv(self.file_path)
        except Exception as e:
            raise ValueError(f"Failed to load diet data: {e}")

        # Parse dates
        if 'Date & Time' in self.df.columns:
            self.df['date'] = pd.to_datetime(self.df['Date & Time']).dt.date
        elif 'Date' in self.df.columns:
            self.df['date'] = pd.to_datetime(self.df['Date']).dt.date
        else:
            raise ValueError("Diet file missing 'Date' or 'Date & Time' column")

    def get_weekly_summary(
        self,
        start_date: date,
        end_date: date,
        calorie_target: int,
        protein_target: int
    ) -> Dict:
        """
        Get diet summary for a date range.

        Args:
            start_date: Start of the week
            end_date: End of the week
            calorie_target: Daily calorie target
            protein_target: Daily protein target

        Returns:
            Dictionary with daily data and summary stats
        """
        if self.df is None:
            raise RuntimeError("Data not loaded. Call load_data() first.")

        # Filter to date range
        mask = (self.df['date'] >= start_date) & (self.df['date'] <= end_date)
        week_data = self.df[mask].copy()

        if week_data.empty:
            return {
                'daily_data': [],
                'summary': {
                    'days_within_calorie_target': 0,
                    'days_hitting_protein_target': 0,
                    'average_calories': 0,
                    'average_protein': 0,
                    'total_days': 0
                }
            }

        # Group by date and sum nutrients
        daily_summary = week_data.groupby('date').agg({
            'Calories, cals': 'sum',
            'Total Carbs, g': 'sum',
            'Protein, g': 'sum',
            'Total Fat, g': 'sum',
            'Dietary Fiber, g': 'sum'
        }).reset_index()

        # Rename columns
        daily_summary.columns = ['date', 'calories', 'carbs', 'protein', 'fats', 'fiber']

        # Add day of week
        daily_summary['day'] = daily_summary['date'].apply(
            lambda d: datetime.combine(d, datetime.min.time()).strftime('%A')
        )

        # Round values
        for col in ['calories', 'carbs', 'protein', 'fats', 'fiber']:
            daily_summary[col] = daily_summary[col].round(0).astype(int)

        # Calculate summary statistics
        days_within_calorie = len(daily_summary[daily_summary['calories'] <= calorie_target])
        days_hitting_protein = len(daily_summary[daily_summary['protein'] >= protein_target])
        avg_calories = daily_summary['calories'].mean()
        avg_protein = daily_summary['protein'].mean()
        total_days = len(daily_summary)

        # Convert to list of dictionaries for easier template use
        daily_data = daily_summary.to_dict('records')

        return {
            'daily_data': daily_data,
            'summary': {
                'days_within_calorie_target': f"{days_within_calorie}/{total_days}",
                'days_hitting_protein_target': f"{days_hitting_protein}/{total_days}",
                'average_calories': int(avg_calories) if not pd.isna(avg_calories) else 0,
                'average_protein': int(avg_protein) if not pd.isna(avg_protein) else 0,
                'total_days': total_days,
                'calorie_target': calorie_target,
                'protein_target': protein_target
            }
        }

    def generate_markdown_table(self, daily_data: List[Dict]) -> str:
        """
        Generate markdown table for diet data.

        Args:
            daily_data: List of daily diet dictionaries

        Returns:
            Markdown formatted table
        """
        if not daily_data:
            return "*No diet data found for this period*\n"

        # Table header
        table = "| Date        | Day       | Calories | Carbs | Protein | Fats | Fiber |\n"
        table += "|-------------|-----------|----------|-------|---------|------|-------|\n"

        # Table rows
        for day in daily_data:
            date_str = day['date'].strftime('%b %d %Y')
            table += (
                f"| {date_str:<11} | {day['day']:<9} | "
                f"{day['calories']:<8} | {day['carbs']:<5} | "
                f"{day['protein']:<7} | {day['fats']:<4} | {day['fiber']:<5} |\n"
            )

        return table


def parse_diet_data(
    file_path: str,
    start_date: date,
    end_date: date,
    calorie_target: int,
    protein_target: int
) -> Tuple[str, Dict]:
    """
    Convenience function to parse diet data and generate output.

    Args:
        file_path: Path to diet data file
        start_date: Start of the week
        end_date: End of the week
        calorie_target: Daily calorie target
        protein_target: Daily protein target

    Returns:
        Tuple of (markdown_table, summary_dict)
    """
    parser = DietParser(file_path)
    parser.load_data()

    result = parser.get_weekly_summary(start_date, end_date, calorie_target, protein_target)

    markdown_table = parser.generate_markdown_table(result['daily_data'])

    return markdown_table, result['summary']
