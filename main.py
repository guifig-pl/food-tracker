#!/usr/bin/env python3
"""
Food Tracker CLI Application

A command-line application for tracking meals, calories, and macronutrients.

Features:
- Log meals with food items, portions, and timestamps
- Track calories and macronutrients (protein, carbs, fats)
- Search and favorite foods for quick access
- Set daily calorie goals based on fitness goals
- Mark off days with categorized reasons
- Weekly and monthly analytics
- Data export/import for backup

Usage:
    python main.py

    Or if made executable:
    ./main.py
"""

from cli import run

if __name__ == "__main__":
    run()
