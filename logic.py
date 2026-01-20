"""
Business logic module for Food Tracker CLI.
Handles calculations, goal management, and analytics.
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from database import (
    get_meals_for_date, get_meals_for_date_range,
    get_off_days_in_range, is_off_day, get_setting, set_setting,
    get_all_settings, get_weight_history, get_latest_weight
)


# ============== Goal Types and Calorie Recommendations ==============

GOAL_TYPES = {
    'bulking': {
        'name': 'Bulking',
        'description': 'Gain muscle mass with calorie surplus',
        'calorie_modifier': 300,  # Add 300 calories above maintenance
        'protein_per_lb': 1.0,    # 1g per lb of body weight
    },
    'cutting': {
        'name': 'Cutting',
        'description': 'Lose fat with calorie deficit',
        'calorie_modifier': -500,  # 500 calorie deficit
        'protein_per_lb': 1.2,     # Higher protein to preserve muscle
    },
    'maintenance': {
        'name': 'Maintenance',
        'description': 'Maintain current weight',
        'calorie_modifier': 0,
        'protein_per_lb': 0.8,
    }
}

MEAL_TYPES = ['breakfast', 'lunch', 'dinner', 'snack']


def get_current_goal() -> str:
    """Get the current goal type."""
    return get_setting('goal_type', 'maintenance')


def set_goal(goal_type: str) -> bool:
    """Set the user's fitness goal. Returns True if valid goal."""
    if goal_type.lower() not in GOAL_TYPES:
        return False
    set_setting('goal_type', goal_type.lower())
    return True


def get_goal_info(goal_type: str = None) -> dict:
    """Get information about a goal type."""
    if goal_type is None:
        goal_type = get_current_goal()
    return GOAL_TYPES.get(goal_type.lower(), GOAL_TYPES['maintenance'])


def calculate_recommended_calories(base_maintenance: int = 2000) -> int:
    """Calculate recommended daily calories based on current goal."""
    goal_type = get_current_goal()
    goal_info = get_goal_info(goal_type)
    return base_maintenance + goal_info['calorie_modifier']


def get_daily_targets() -> dict:
    """Get current daily targets from settings."""
    settings = get_all_settings()
    return {
        'calories': int(settings.get('daily_calorie_target', 2000)),
        'protein': int(settings.get('protein_target', 150)),
        'carbs': int(settings.get('carbs_target', 200)),
        'fats': int(settings.get('fats_target', 65)),
    }


def set_daily_targets(calories: int = None, protein: int = None,
                      carbs: int = None, fats: int = None):
    """Set daily nutrition targets."""
    if calories is not None:
        set_setting('daily_calorie_target', str(calories))
    if protein is not None:
        set_setting('protein_target', str(protein))
    if carbs is not None:
        set_setting('carbs_target', str(carbs))
    if fats is not None:
        set_setting('fats_target', str(fats))


# ============== Daily Calculations ==============

def calculate_daily_totals(target_date: date = None) -> dict:
    """Calculate total nutrition for a specific date."""
    if target_date is None:
        target_date = date.today()

    meals = get_meals_for_date(target_date)

    totals = {
        'calories': 0.0,
        'protein': 0.0,
        'carbs': 0.0,
        'fats': 0.0,
        'meal_count': len(meals),
        'is_off_day': is_off_day(target_date),
    }

    for meal in meals:
        portions = meal['portions']
        totals['calories'] += meal['calories'] * portions
        totals['protein'] += meal['protein'] * portions
        totals['carbs'] += meal['carbs'] * portions
        totals['fats'] += meal['fats'] * portions

    return totals


def calculate_daily_progress(target_date: date = None) -> dict:
    """Calculate progress toward daily goals."""
    if target_date is None:
        target_date = date.today()

    totals = calculate_daily_totals(target_date)
    targets = get_daily_targets()

    progress = {
        'totals': totals,
        'targets': targets,
        'remaining': {
            'calories': targets['calories'] - totals['calories'],
            'protein': targets['protein'] - totals['protein'],
            'carbs': targets['carbs'] - totals['carbs'],
            'fats': targets['fats'] - totals['fats'],
        },
        'percentage': {
            'calories': (totals['calories'] / targets['calories'] * 100) if targets['calories'] > 0 else 0,
            'protein': (totals['protein'] / targets['protein'] * 100) if targets['protein'] > 0 else 0,
            'carbs': (totals['carbs'] / targets['carbs'] * 100) if targets['carbs'] > 0 else 0,
            'fats': (totals['fats'] / targets['fats'] * 100) if targets['fats'] > 0 else 0,
        },
        'is_off_day': totals['is_off_day'],
    }

    # Calculate surplus/deficit
    progress['deficit_surplus'] = totals['calories'] - targets['calories']

    return progress


def get_meals_by_type(target_date: date = None) -> dict:
    """Get meals organized by meal type for a date."""
    if target_date is None:
        target_date = date.today()

    meals = get_meals_for_date(target_date)
    by_type = defaultdict(list)

    for meal in meals:
        by_type[meal['meal_type']].append(meal)

    return dict(by_type)


# ============== Weekly/Monthly Analytics ==============

def get_week_start(target_date: date = None) -> date:
    """Get the Monday of the week containing the target date."""
    if target_date is None:
        target_date = date.today()
    return target_date - timedelta(days=target_date.weekday())


def get_month_start(target_date: date = None) -> date:
    """Get the first day of the month containing the target date."""
    if target_date is None:
        target_date = date.today()
    return target_date.replace(day=1)


def calculate_weekly_averages(week_start: date = None) -> dict:
    """Calculate average nutrition for a week."""
    if week_start is None:
        week_start = get_week_start()

    week_end = week_start + timedelta(days=6)
    meals = get_meals_for_date_range(week_start, week_end)
    off_days = get_off_days_in_range(week_start, week_end)

    # Group meals by date
    daily_totals = defaultdict(lambda: {
        'calories': 0.0, 'protein': 0.0, 'carbs': 0.0, 'fats': 0.0
    })

    for meal in meals:
        meal_date = datetime.fromisoformat(meal['logged_at']).date().isoformat()
        portions = meal['portions']
        daily_totals[meal_date]['calories'] += meal['calories'] * portions
        daily_totals[meal_date]['protein'] += meal['protein'] * portions
        daily_totals[meal_date]['carbs'] += meal['carbs'] * portions
        daily_totals[meal_date]['fats'] += meal['fats'] * portions

    off_day_dates = {od['date'] for od in off_days}
    tracked_days = 0
    total_calories = 0.0
    total_protein = 0.0
    total_carbs = 0.0
    total_fats = 0.0

    current = week_start
    while current <= week_end:
        date_str = current.isoformat()
        if date_str not in off_day_dates:
            if date_str in daily_totals or current <= date.today():
                tracked_days += 1
                if date_str in daily_totals:
                    total_calories += daily_totals[date_str]['calories']
                    total_protein += daily_totals[date_str]['protein']
                    total_carbs += daily_totals[date_str]['carbs']
                    total_fats += daily_totals[date_str]['fats']
        current += timedelta(days=1)

    return {
        'week_start': week_start,
        'week_end': week_end,
        'tracked_days': tracked_days,
        'off_day_count': len(off_days),
        'off_days': off_days,
        'totals': {
            'calories': total_calories,
            'protein': total_protein,
            'carbs': total_carbs,
            'fats': total_fats,
        },
        'averages': {
            'calories': total_calories / tracked_days if tracked_days > 0 else 0,
            'protein': total_protein / tracked_days if tracked_days > 0 else 0,
            'carbs': total_carbs / tracked_days if tracked_days > 0 else 0,
            'fats': total_fats / tracked_days if tracked_days > 0 else 0,
        },
        'daily_breakdown': dict(daily_totals),
    }


def calculate_monthly_averages(month_start: date = None) -> dict:
    """Calculate average nutrition for a month."""
    if month_start is None:
        month_start = get_month_start()

    # Get end of month
    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1)
    month_end = next_month - timedelta(days=1)

    meals = get_meals_for_date_range(month_start, month_end)
    off_days = get_off_days_in_range(month_start, month_end)

    # Group meals by date
    daily_totals = defaultdict(lambda: {
        'calories': 0.0, 'protein': 0.0, 'carbs': 0.0, 'fats': 0.0
    })

    for meal in meals:
        meal_date = datetime.fromisoformat(meal['logged_at']).date().isoformat()
        portions = meal['portions']
        daily_totals[meal_date]['calories'] += meal['calories'] * portions
        daily_totals[meal_date]['protein'] += meal['protein'] * portions
        daily_totals[meal_date]['carbs'] += meal['carbs'] * portions
        daily_totals[meal_date]['fats'] += meal['fats'] * portions

    off_day_dates = {od['date'] for od in off_days}
    tracked_days = 0
    total_calories = 0.0
    total_protein = 0.0
    total_carbs = 0.0
    total_fats = 0.0

    current = month_start
    while current <= min(month_end, date.today()):
        date_str = current.isoformat()
        if date_str not in off_day_dates:
            tracked_days += 1
            if date_str in daily_totals:
                total_calories += daily_totals[date_str]['calories']
                total_protein += daily_totals[date_str]['protein']
                total_carbs += daily_totals[date_str]['carbs']
                total_fats += daily_totals[date_str]['fats']
        current += timedelta(days=1)

    return {
        'month_start': month_start,
        'month_end': month_end,
        'month_name': month_start.strftime('%B %Y'),
        'tracked_days': tracked_days,
        'off_day_count': len(off_days),
        'off_days': off_days,
        'totals': {
            'calories': total_calories,
            'protein': total_protein,
            'carbs': total_carbs,
            'fats': total_fats,
        },
        'averages': {
            'calories': total_calories / tracked_days if tracked_days > 0 else 0,
            'protein': total_protein / tracked_days if tracked_days > 0 else 0,
            'carbs': total_carbs / tracked_days if tracked_days > 0 else 0,
            'fats': total_fats / tracked_days if tracked_days > 0 else 0,
        },
    }


def get_weekly_breakdown(num_weeks: int = 4) -> List[dict]:
    """Get week-by-week breakdown for the dashboard."""
    weeks = []
    current_week_start = get_week_start()

    for i in range(num_weeks):
        week_start = current_week_start - timedelta(weeks=i)
        week_data = calculate_weekly_averages(week_start)
        weeks.append(week_data)

    return weeks


def get_monthly_breakdown(num_months: int = 3) -> List[dict]:
    """Get month-by-month breakdown for the dashboard."""
    months = []
    current_month = get_month_start()

    for i in range(num_months):
        if i == 0:
            month_start = current_month
        else:
            # Go back i months
            year = current_month.year
            month = current_month.month - i
            while month <= 0:
                month += 12
                year -= 1
            month_start = date(year, month, 1)

        month_data = calculate_monthly_averages(month_start)
        months.append(month_data)

    return months


# ============== Weight Progress ==============

def calculate_weight_progress() -> dict:
    """Calculate weight change progress."""
    history = get_weight_history(limit=30)

    if not history:
        return {
            'current_weight': None,
            'starting_weight': None,
            'change': None,
            'trend': None,
        }

    current = history[0]['weight']
    starting = history[-1]['weight'] if len(history) > 1 else current
    change = current - starting

    # Calculate 7-day trend
    recent = [h['weight'] for h in history[:7]]
    if len(recent) >= 2:
        trend = recent[0] - recent[-1]
    else:
        trend = 0

    return {
        'current_weight': current,
        'starting_weight': starting,
        'change': change,
        'trend': trend,
        'trend_direction': 'gaining' if trend > 0 else 'losing' if trend < 0 else 'stable',
        'history': history,
    }


# ============== Utility Functions ==============

def get_streak() -> int:
    """Calculate current tracking streak (consecutive days logged)."""
    streak = 0
    current = date.today()

    while True:
        if is_off_day(current):
            current -= timedelta(days=1)
            continue

        meals = get_meals_for_date(current)
        if meals:
            streak += 1
            current -= timedelta(days=1)
        else:
            break

    return streak


def format_macro_ratio(protein: float, carbs: float, fats: float) -> str:
    """Format macros as a ratio string (e.g., '40/30/30')."""
    total = protein + carbs + fats
    if total == 0:
        return "0/0/0"

    p_pct = int(round(protein / total * 100))
    c_pct = int(round(carbs / total * 100))
    f_pct = int(round(fats / total * 100))

    return f"{p_pct}/{c_pct}/{f_pct}"
