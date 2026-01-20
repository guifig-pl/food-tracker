"""
Flask REST API for Food Tracker Web Application.
Provides endpoints for all food tracking operations.
"""

import sys
from pathlib import Path

# Add parent directory to path to import existing modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime, date, timedelta
import json

import database as db
import logic

app = Flask(__name__,
            static_folder='../static',
            template_folder='../templates')
CORS(app)

# Initialize database on startup
db.init_database()


# ============== Helper Functions ==============

def parse_date(date_str):
    """Parse date string to date object."""
    if not date_str or date_str == 'today':
        return date.today()
    if date_str == 'yesterday':
        return date.today() - timedelta(days=1)
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None


def json_response(data, status=200):
    """Create a JSON response."""
    return jsonify(data), status


def error_response(message, status=400):
    """Create an error response."""
    return jsonify({'error': message}), status


# ============== Static Files & PWA ==============

@app.route('/')
def index():
    """Serve the main HTML page."""
    return send_from_directory('../templates', 'index.html')


@app.route('/manifest.json')
def manifest():
    """Serve PWA manifest."""
    return send_from_directory('../static', 'manifest.json')


@app.route('/sw.js')
def service_worker():
    """Serve service worker from root."""
    return send_from_directory('../static/js', 'sw.js')


# ============== Food Endpoints ==============

@app.route('/api/foods', methods=['GET'])
def get_foods():
    """Get all foods or search by query."""
    query = request.args.get('q', '')
    limit = request.args.get('limit', 100, type=int)

    if query:
        foods = db.search_foods(query, limit)
    else:
        foods = db.get_all_foods(limit)

    return json_response({'foods': foods})


@app.route('/api/foods/<int:food_id>', methods=['GET'])
def get_food(food_id):
    """Get a single food by ID."""
    food = db.get_food(food_id)
    if not food:
        return error_response('Food not found', 404)
    return json_response({'food': food})


@app.route('/api/foods', methods=['POST'])
def add_food():
    """Add a new food."""
    data = request.get_json()

    if not data or not data.get('name'):
        return error_response('Food name is required')

    try:
        food_id = db.add_food(
            name=data['name'],
            calories=data.get('calories', 0),
            protein=data.get('protein', 0),
            carbs=data.get('carbs', 0),
            fats=data.get('fats', 0),
            serving_size=data.get('serving_size', '1 serving')
        )
        food = db.get_food(food_id)
        return json_response({'food': food, 'message': 'Food added successfully'}, 201)
    except Exception as e:
        return error_response(str(e))


@app.route('/api/foods/<int:food_id>', methods=['PUT'])
def update_food(food_id):
    """Update an existing food."""
    data = request.get_json()

    if not data:
        return error_response('No data provided')

    success = db.update_food(
        food_id,
        name=data.get('name'),
        calories=data.get('calories'),
        protein=data.get('protein'),
        carbs=data.get('carbs'),
        fats=data.get('fats'),
        serving_size=data.get('serving_size')
    )

    if success:
        food = db.get_food(food_id)
        return json_response({'food': food, 'message': 'Food updated'})
    return error_response('Food not found', 404)


@app.route('/api/foods/<int:food_id>', methods=['DELETE'])
def delete_food(food_id):
    """Delete a food."""
    if db.delete_food(food_id):
        return json_response({'message': 'Food deleted'})
    return error_response('Food not found', 404)


@app.route('/api/foods/<int:food_id>/favorite', methods=['POST'])
def toggle_favorite(food_id):
    """Toggle favorite status of a food."""
    is_favorite = db.toggle_favorite(food_id)
    return json_response({'is_favorite': is_favorite})


@app.route('/api/foods/favorites', methods=['GET'])
def get_favorites():
    """Get all favorite foods."""
    foods = db.get_favorite_foods()
    return json_response({'foods': foods})


@app.route('/api/foods/recent', methods=['GET'])
def get_recent_foods():
    """Get recently logged foods."""
    limit = request.args.get('limit', 10, type=int)
    foods = db.get_recent_foods(limit)
    return json_response({'foods': foods})


# ============== Meal Log Endpoints ==============

@app.route('/api/meals', methods=['GET'])
def get_meals():
    """Get meals for a date or date range."""
    date_str = request.args.get('date', 'today')
    start_str = request.args.get('start')
    end_str = request.args.get('end')

    if start_str and end_str:
        start_date = parse_date(start_str)
        end_date = parse_date(end_str)
        if not start_date or not end_date:
            return error_response('Invalid date format')
        meals = db.get_meals_for_date_range(start_date, end_date)
    else:
        target_date = parse_date(date_str)
        if not target_date:
            return error_response('Invalid date format')
        meals = db.get_meals_for_date(target_date)

    return json_response({'meals': meals})


@app.route('/api/meals', methods=['POST'])
def log_meal():
    """Log a new meal."""
    data = request.get_json()

    if not data or not data.get('food_id'):
        return error_response('Food ID is required')

    try:
        logged_at = None
        if data.get('logged_at'):
            logged_at = datetime.fromisoformat(data['logged_at'])
        elif data.get('date'):
            log_date = parse_date(data['date'])
            if log_date:
                logged_at = datetime.combine(log_date, datetime.now().time())

        log_id = db.log_meal(
            food_id=data['food_id'],
            portions=data.get('portions', 1.0),
            meal_type=data.get('meal_type', 'snack'),
            logged_at=logged_at,
            notes=data.get('notes')
        )

        return json_response({'log_id': log_id, 'message': 'Meal logged'}, 201)
    except Exception as e:
        return error_response(str(e))


@app.route('/api/meals/<int:log_id>', methods=['DELETE'])
def delete_meal(log_id):
    """Delete a meal log."""
    if db.delete_meal_log(log_id):
        return json_response({'message': 'Meal deleted'})
    return error_response('Meal not found', 404)


# ============== Multi-Ingredient Meal Endpoints ==============

@app.route('/api/meals/multi', methods=['POST'])
def create_multi_meal():
    """Create a multi-ingredient meal."""
    data = request.get_json()

    if not data or not data.get('ingredients'):
        return error_response('Ingredients are required')

    if not isinstance(data['ingredients'], list) or len(data['ingredients']) == 0:
        return error_response('At least one ingredient is required')

    try:
        logged_at = None
        if data.get('logged_at'):
            logged_at = datetime.fromisoformat(data['logged_at'])
        elif data.get('date'):
            log_date = parse_date(data['date'])
            if log_date:
                logged_at = datetime.combine(log_date, datetime.now().time())

        meal_id = db.create_multi_meal(
            name=data.get('name', ''),
            meal_type=data.get('meal_type', 'lunch'),
            ingredients=data['ingredients'],
            logged_at=logged_at,
            notes=data.get('notes')
        )

        # Get the created meal with details
        meal = db.get_meal(meal_id)

        return json_response({
            'meal_id': meal_id,
            'meal': meal,
            'message': 'Multi-ingredient meal logged'
        }, 201)
    except Exception as e:
        return error_response(str(e))


@app.route('/api/meals/multi/<int:meal_id>', methods=['GET'])
def get_multi_meal(meal_id):
    """Get a multi-ingredient meal with all its ingredients."""
    meal = db.get_meal(meal_id)
    if not meal:
        return error_response('Meal not found', 404)
    return json_response({'meal': meal})


@app.route('/api/meals/multi/<int:meal_id>', methods=['DELETE'])
def delete_multi_meal(meal_id):
    """Delete a multi-ingredient meal."""
    if db.delete_multi_meal(meal_id):
        return json_response({'message': 'Meal deleted'})
    return error_response('Meal not found', 404)


@app.route('/api/meals/all', methods=['GET'])
def get_all_meals():
    """Get all meals for a date (both single and multi-ingredient)."""
    date_str = request.args.get('date', 'today')
    target_date = parse_date(date_str)

    if not target_date:
        return error_response('Invalid date format')

    all_meals = db.get_all_meals_for_date(target_date)

    return json_response({
        'date': target_date.isoformat(),
        'single_logs': all_meals['single_logs'],
        'multi_meals': all_meals['multi_meals']
    })


# ============== Daily Progress Endpoints ==============

@app.route('/api/progress/daily', methods=['GET'])
def get_daily_progress():
    """Get daily progress with totals and targets."""
    date_str = request.args.get('date', 'today')
    target_date = parse_date(date_str)

    if not target_date:
        return error_response('Invalid date format')

    progress = logic.calculate_daily_progress(target_date)
    single_meals = db.get_meals_for_date(target_date)
    multi_meals = db.get_multi_meals_for_date(target_date)
    off_day = db.get_off_day(target_date)

    # Add multi-meal totals to progress
    for meal in multi_meals:
        progress['totals']['calories'] += meal['total_calories']
        progress['totals']['protein'] += meal['total_protein']
        progress['totals']['carbs'] += meal['total_carbs']
        progress['totals']['fats'] += meal['total_fats']
        progress['totals']['meal_count'] += 1

    # Recalculate percentages and deficit/surplus
    targets = progress['targets']
    totals = progress['totals']
    progress['percentage'] = {
        'calories': (totals['calories'] / targets['calories'] * 100) if targets['calories'] > 0 else 0,
        'protein': (totals['protein'] / targets['protein'] * 100) if targets['protein'] > 0 else 0,
        'carbs': (totals['carbs'] / targets['carbs'] * 100) if targets['carbs'] > 0 else 0,
        'fats': (totals['fats'] / targets['fats'] * 100) if targets['fats'] > 0 else 0,
    }
    progress['remaining'] = {
        'calories': targets['calories'] - totals['calories'],
        'protein': targets['protein'] - totals['protein'],
        'carbs': targets['carbs'] - totals['carbs'],
        'fats': targets['fats'] - totals['fats'],
    }
    progress['deficit_surplus'] = totals['calories'] - targets['calories']

    return json_response({
        'date': target_date.isoformat(),
        'progress': progress,
        'meals': single_meals,
        'multi_meals': multi_meals,
        'off_day': off_day
    })


@app.route('/api/progress/weekly', methods=['GET'])
def get_weekly_progress():
    """Get weekly progress and averages."""
    date_str = request.args.get('date')

    if date_str:
        target_date = parse_date(date_str)
        week_start = logic.get_week_start(target_date)
    else:
        week_start = logic.get_week_start()

    weekly = logic.calculate_weekly_averages(week_start)

    # Convert date objects to strings for JSON
    weekly['week_start'] = weekly['week_start'].isoformat()
    weekly['week_end'] = weekly['week_end'].isoformat()

    return json_response({'weekly': weekly})


@app.route('/api/progress/monthly', methods=['GET'])
def get_monthly_progress():
    """Get monthly progress and averages."""
    date_str = request.args.get('date')

    if date_str:
        target_date = parse_date(date_str)
        month_start = logic.get_month_start(target_date)
    else:
        month_start = logic.get_month_start()

    monthly = logic.calculate_monthly_averages(month_start)

    # Convert date objects to strings
    monthly['month_start'] = monthly['month_start'].isoformat()
    monthly['month_end'] = monthly['month_end'].isoformat()

    return json_response({'monthly': monthly})


@app.route('/api/analytics/breakdown', methods=['GET'])
def get_analytics_breakdown():
    """Get week-by-week and month-by-month breakdown."""
    num_weeks = request.args.get('weeks', 4, type=int)
    num_months = request.args.get('months', 3, type=int)

    weeks = logic.get_weekly_breakdown(num_weeks)
    months = logic.get_monthly_breakdown(num_months)

    # Convert dates to strings
    for week in weeks:
        week['week_start'] = week['week_start'].isoformat()
        week['week_end'] = week['week_end'].isoformat()

    for month in months:
        month['month_start'] = month['month_start'].isoformat()
        month['month_end'] = month['month_end'].isoformat()

    return json_response({
        'weeks': weeks,
        'months': months
    })


# ============== Settings Endpoints ==============

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get all settings."""
    settings = db.get_all_settings()
    goal_info = logic.get_goal_info(settings.get('goal_type', 'maintenance'))

    return json_response({
        'settings': settings,
        'goal_info': goal_info,
        'goal_types': logic.GOAL_TYPES
    })


@app.route('/api/settings', methods=['PUT'])
def update_settings():
    """Update settings."""
    data = request.get_json()

    if not data:
        return error_response('No data provided')

    for key, value in data.items():
        db.set_setting(key, str(value))

    return json_response({'message': 'Settings updated'})


@app.route('/api/settings/goal', methods=['PUT'])
def update_goal():
    """Update fitness goal."""
    data = request.get_json()
    goal_type = data.get('goal_type')

    if not goal_type or goal_type not in logic.GOAL_TYPES:
        return error_response('Invalid goal type')

    logic.set_goal(goal_type)

    return json_response({
        'message': 'Goal updated',
        'goal_info': logic.get_goal_info(goal_type)
    })


# ============== Off Days Endpoints ==============

@app.route('/api/off-days', methods=['GET'])
def get_off_days():
    """Get off days in a date range."""
    start_str = request.args.get('start')
    end_str = request.args.get('end')

    if start_str and end_str:
        start_date = parse_date(start_str)
        end_date = parse_date(end_str)
    else:
        # Default to current month
        start_date = logic.get_month_start()
        if start_date.month == 12:
            next_month = start_date.replace(year=start_date.year + 1, month=1)
        else:
            next_month = start_date.replace(month=start_date.month + 1)
        end_date = next_month - timedelta(days=1)

    off_days = db.get_off_days_in_range(start_date, end_date)

    return json_response({
        'off_days': off_days,
        'reasons': db.OFF_DAY_REASONS
    })


@app.route('/api/off-days', methods=['POST'])
def add_off_day():
    """Add an off day."""
    data = request.get_json()

    if not data or not data.get('date'):
        return error_response('Date is required')

    target_date = parse_date(data['date'])
    if not target_date:
        return error_response('Invalid date format')

    reason = data.get('reason', 'other')
    notes = data.get('notes')

    db.add_off_day(target_date, reason, notes)

    return json_response({'message': 'Off day added'}, 201)


@app.route('/api/off-days/<date_str>', methods=['DELETE'])
def remove_off_day(date_str):
    """Remove an off day."""
    target_date = parse_date(date_str)
    if not target_date:
        return error_response('Invalid date format')

    if db.remove_off_day(target_date):
        return json_response({'message': 'Off day removed'})
    return error_response('Off day not found', 404)


# ============== Weight Endpoints ==============

@app.route('/api/weight', methods=['GET'])
def get_weight_history():
    """Get weight history."""
    limit = request.args.get('limit', 30, type=int)
    history = db.get_weight_history(limit)
    progress = logic.calculate_weight_progress()

    return json_response({
        'history': history,
        'progress': progress
    })


@app.route('/api/weight', methods=['POST'])
def log_weight():
    """Log a weight entry."""
    data = request.get_json()

    if not data or not data.get('weight'):
        return error_response('Weight is required')

    recorded_at = None
    if data.get('date'):
        recorded_at = parse_date(data['date'])

    db.log_weight(
        weight=data['weight'],
        recorded_at=recorded_at,
        notes=data.get('notes')
    )

    return json_response({'message': 'Weight logged'}, 201)


# ============== Data Export/Import ==============

@app.route('/api/export', methods=['GET'])
def export_data():
    """Export all data as JSON."""
    data = db.export_data()
    return json_response(data)


@app.route('/api/import', methods=['POST'])
def import_data():
    """Import data from JSON."""
    data = request.get_json()

    if not data:
        return error_response('No data provided')

    merge = request.args.get('merge', 'true').lower() == 'true'

    try:
        db.import_data(data, merge=merge)
        return json_response({'message': 'Data imported successfully'})
    except Exception as e:
        return error_response(str(e))


# ============== Bulk Import Endpoint ==============

@app.route('/api/foods/import', methods=['POST'])
def import_foods_bulk():
    """Bulk import foods into the database."""
    data = request.get_json()

    if not data or not data.get('foods'):
        return error_response('Foods list is required')

    foods_list = data['foods']
    if not isinstance(foods_list, list):
        return error_response('Foods must be a list')

    skip_duplicates = data.get('skip_duplicates', True)

    try:
        result = db.import_foods_bulk(foods_list, skip_duplicates=skip_duplicates)
        return json_response({
            'message': 'Foods imported',
            'added': result['added'],
            'skipped': result['skipped'],
            'updated': result['updated']
        })
    except Exception as e:
        return error_response(str(e))


# ============== Utility Endpoints ==============

@app.route('/api/streak', methods=['GET'])
def get_streak():
    """Get current tracking streak."""
    streak = logic.get_streak()
    return json_response({'streak': streak})


@app.route('/api/meal-types', methods=['GET'])
def get_meal_types():
    """Get available meal types."""
    return json_response({'meal_types': logic.MEAL_TYPES})


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
