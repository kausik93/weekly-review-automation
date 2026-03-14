#!/usr/bin/env python3
"""
Unit tests for weekly review automation script.

Run with: pytest test_weekly_review.py
"""

import pytest
import pandas as pd
from datetime import date, datetime
from pathlib import Path
import tempfile
import os

# Import modules to test
from diet_parser import DietParser
from exercise_parser import ExerciseParser
from ticktick_client import TickTickClient
from markdown_generator import MarkdownGenerator


class TestDietParser:
    """Tests for diet data parsing."""

    def test_parse_empty_data(self):
        """Test parsing when no data is in the date range."""
        # Create a temporary CSV with data outside the range
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("Date & Time,Calories, cals,Total Carbs, g,Protein, g,Total Fat, g,Dietary Fiber, g,Meal\n")
            f.write("2025-01-01 08:00,500,50,30,10,5,Breakfast\n")
            temp_file = f.name

        try:
            parser = DietParser(temp_file)
            parser.load_data()

            result = parser.get_weekly_summary(
                date(2026, 1, 5),
                date(2026, 1, 11),
                1900,
                128
            )

            assert result['summary']['total_days'] == 0
            assert len(result['daily_data']) == 0
        finally:
            os.unlink(temp_file)

    def test_markdown_table_generation(self):
        """Test markdown table generation."""
        parser = DietParser("dummy.csv")

        daily_data = [
            {
                'date': date(2026, 1, 5),
                'day': 'Sunday',
                'calories': 1850,
                'carbs': 180,
                'protein': 130,
                'fats': 45,
                'fiber': 25
            }
        ]

        table = parser.generate_markdown_table(daily_data)

        assert "| Date" in table
        assert "| Jan 05 2026" in table
        assert "Sunday" in table
        assert "1850" in table


class TestExerciseParser:
    """Tests for exercise data parsing."""

    def test_parse_empty_data(self):
        """Test parsing when no workouts in the date range."""
        # Create a temporary CSV with data outside the range
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("title,start_time,end_time,exercise_title\n")
            f.write("Workout,\"01 Jan 2025, 08:00\",\"01 Jan 2025, 09:00\",Squats\n")
            temp_file = f.name

        try:
            parser = ExerciseParser(temp_file)
            parser.load_data()

            result = parser.get_weekly_summary(
                date(2026, 1, 5),
                date(2026, 1, 11),
                4
            )

            assert result['summary']['total_sessions'] == 0
            assert len(result['workouts']) == 0
        finally:
            os.unlink(temp_file)

    def test_duration_formatting(self):
        """Test workout duration formatting."""
        assert ExerciseParser._format_duration(30) == "30 mins"
        assert ExerciseParser._format_duration(60) == "1 hr"
        assert ExerciseParser._format_duration(90) == "1 hr 30 mins"
        assert ExerciseParser._format_duration(150) == "2 hrs 30 mins"


class TestTickTickClient:
    """Tests for TickTick client."""

    def test_process_goal_detection(self):
        """Test process goal vs discrete task classification."""
        assert TickTickClient._is_process_goal("Go to gym every week") == True
        assert TickTickClient._is_process_goal("Exercise 3 days a week") == True
        assert TickTickClient._is_process_goal("Daily meditation") == True
        assert TickTickClient._is_process_goal("Complete the project") == False
        assert TickTickClient._is_process_goal("Finish reading book") == False

    def test_group_tasks_by_domain(self):
        """Test task grouping by domain prefix."""
        client = TickTickClient("test", "test")

        tasks = [
            {'title': '[Health] Run a 5k', 'status': 2, 'id': '1'},
            {'title': '[Health] Stretch every day', 'status': 0, 'id': '2'},
            {'title': '[Work] Complete project', 'status': 0, 'id': '3'},
        ]

        domains = [
            {'name': 'Health', 'prefix': '[Health]'},
            {'name': 'Work', 'prefix': '[Work]'}
        ]

        result = client.group_tasks_by_domain(tasks, domains)

        assert len(result['Health']['discrete_tasks']) == 1
        assert len(result['Health']['process_goals']) == 1
        assert result['Health']['discrete_tasks'][0]['completed'] == True
        assert result['Health']['discrete_tasks'][0]['title'] == 'Run a 5k'

        assert len(result['Work']['discrete_tasks']) == 1
        assert result['Work']['discrete_tasks'][0]['title'] == 'Complete project'


class TestMarkdownGenerator:
    """Tests for markdown generation."""

    def test_generate_basic_review(self):
        """Test basic markdown generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = MarkdownGenerator(tmpdir, "reviews")

            content = generator.generate_review(
                start_date=date(2026, 1, 5),
                end_date=date(2026, 1, 11),
                diet_table="| Date | Calories |\n|------|----------|\n",
                diet_summary={
                    'days_within_calorie_target': '5/7',
                    'days_hitting_protein_target': '4/7',
                    'average_calories': 1850,
                    'average_protein': 125,
                    'calorie_target': 1900,
                    'protein_target': 128
                },
                diet_observations="",
                exercise_summary="- Workout 1\n",
                exercise_stats={
                    'sessions_ratio': '4/4',
                    'workout_days': []
                },
                exercise_observations="",
                goals_by_domain={},
                domain_reflections={}
            )

            assert "## Diet review" in content
            assert "## Exercise review" in content
            assert "## Goals review" in content
            assert "5/7" in content
            assert "4/4" in content

    def test_write_review_dry_run(self):
        """Test dry run mode doesn't create files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = MarkdownGenerator(tmpdir, "reviews")

            path = generator.write_review(
                date(2026, 1, 5),
                "Test content",
                dry_run=True
            )

            # File should not exist in dry run mode
            assert not Path(path).exists()

    def test_write_review_creates_directory(self):
        """Test that write_review creates directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = MarkdownGenerator(tmpdir, "nested/reviews/folder")

            path = generator.write_review(
                date(2026, 1, 5),
                "Test content",
                dry_run=False
            )

            # Directory should be created
            assert Path(path).exists()
            assert Path(path).parent.exists()

            # Content should be written
            with open(path, 'r') as f:
                content = f.read()
            assert content == "Test content"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
