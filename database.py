"""
Database module for Food Tracker CLI.
Handles SQLite database setup and CRUD operations.
"""

import sqlite3
from datetime import datetime, date
from typing import Optional, List, Tuple
from pathlib import Path

DATABASE_PATH = Path.home() / ".food_tracker" / "food_tracker.db"


def get_connection() -> sqlite3.Connection:
    """Get a database connection, creating the database directory if needed."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize the database with all required tables."""
    conn = get_connection()
    cursor = conn.cursor()

    # Foods table - stores all food items with nutritional info
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            calories REAL NOT NULL,
            protein REAL NOT NULL DEFAULT 0,
            carbs REAL NOT NULL DEFAULT 0,
            fats REAL NOT NULL DEFAULT 0,
            serving_size TEXT DEFAULT '1 serving',
            is_favorite INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Meal logs table - records of meals eaten
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meal_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_id INTEGER NOT NULL,
            portions REAL NOT NULL DEFAULT 1.0,
            meal_type TEXT NOT NULL,
            logged_at TIMESTAMP NOT NULL,
            notes TEXT,
            FOREIGN KEY (food_id) REFERENCES foods(id) ON DELETE CASCADE
        )
    """)

    # User settings table - stores user preferences and goals
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # Off days table - tracks days not counted
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS off_days (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL UNIQUE,
            reason TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Weight history table - tracks weight over time
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weight_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            weight REAL NOT NULL,
            recorded_at DATE NOT NULL,
            notes TEXT,
            UNIQUE(recorded_at)
        )
    """)

    # Meals table - groups multiple ingredients into a single meal
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            meal_type TEXT NOT NULL,
            logged_at TIMESTAMP NOT NULL,
            total_calories REAL DEFAULT 0,
            total_protein REAL DEFAULT 0,
            total_carbs REAL DEFAULT 0,
            total_fats REAL DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Meal ingredients table - links foods to meals with amounts
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meal_ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meal_id INTEGER NOT NULL,
            food_id INTEGER NOT NULL,
            amount_grams REAL NOT NULL DEFAULT 100,
            calories REAL NOT NULL,
            protein REAL NOT NULL,
            carbs REAL NOT NULL,
            fats REAL NOT NULL,
            FOREIGN KEY (meal_id) REFERENCES meals(id) ON DELETE CASCADE,
            FOREIGN KEY (food_id) REFERENCES foods(id) ON DELETE CASCADE
        )
    """)

    # Insert default settings if not exists
    default_settings = [
        ('goal_type', 'maintenance'),
        ('daily_calorie_target', '2000'),
        ('protein_target', '150'),
        ('carbs_target', '200'),
        ('fats_target', '65'),
    ]

    for key, value in default_settings:
        cursor.execute("""
            INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)
        """, (key, value))

    conn.commit()
    conn.close()


# ============== Food Operations ==============

def add_food(name: str, calories: float, protein: float = 0,
             carbs: float = 0, fats: float = 0, serving_size: str = "1 serving") -> int:
    """Add a new food to the database. Returns the food ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO foods (name, calories, protein, carbs, fats, serving_size)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, calories, protein, carbs, fats, serving_size))
    food_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return food_id


def update_food(food_id: int, name: str = None, calories: float = None,
                protein: float = None, carbs: float = None, fats: float = None,
                serving_size: str = None) -> bool:
    """Update an existing food. Returns True if successful."""
    conn = get_connection()
    cursor = conn.cursor()

    updates = []
    values = []

    if name is not None:
        updates.append("name = ?")
        values.append(name)
    if calories is not None:
        updates.append("calories = ?")
        values.append(calories)
    if protein is not None:
        updates.append("protein = ?")
        values.append(protein)
    if carbs is not None:
        updates.append("carbs = ?")
        values.append(carbs)
    if fats is not None:
        updates.append("fats = ?")
        values.append(fats)
    if serving_size is not None:
        updates.append("serving_size = ?")
        values.append(serving_size)

    if not updates:
        return False

    values.append(food_id)
    query = f"UPDATE foods SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(query, values)
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def delete_food(food_id: int) -> bool:
    """Delete a food from the database. Returns True if successful."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM foods WHERE id = ?", (food_id,))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def get_food(food_id: int) -> Optional[dict]:
    """Get a single food by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM foods WHERE id = ?", (food_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def search_foods(query: str, limit: int = 20) -> List[dict]:
    """Search foods by name. Returns list of matching foods."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM foods
        WHERE name LIKE ?
        ORDER BY is_favorite DESC, name ASC
        LIMIT ?
    """, (f"%{query}%", limit))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_all_foods(limit: int = 100) -> List[dict]:
    """Get all foods, ordered by favorites first then name."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM foods
        ORDER BY is_favorite DESC, name ASC
        LIMIT ?
    """, (limit,))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_favorite_foods() -> List[dict]:
    """Get all favorite foods."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM foods
        WHERE is_favorite = 1
        ORDER BY name ASC
    """)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def toggle_favorite(food_id: int) -> bool:
    """Toggle the favorite status of a food. Returns new favorite status."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE foods SET is_favorite = NOT is_favorite WHERE id = ?
    """, (food_id,))
    conn.commit()

    cursor.execute("SELECT is_favorite FROM foods WHERE id = ?", (food_id,))
    row = cursor.fetchone()
    conn.close()
    return bool(row['is_favorite']) if row else False


# ============== Meal Log Operations ==============

def log_meal(food_id: int, portions: float, meal_type: str,
             logged_at: datetime = None, notes: str = None) -> int:
    """Log a meal. Returns the meal log ID."""
    if logged_at is None:
        logged_at = datetime.now()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO meal_logs (food_id, portions, meal_type, logged_at, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (food_id, portions, meal_type, logged_at, notes))
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return log_id


def delete_meal_log(log_id: int) -> bool:
    """Delete a meal log. Returns True if successful."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM meal_logs WHERE id = ?", (log_id,))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def get_meals_for_date(target_date: date) -> List[dict]:
    """Get all meals logged for a specific date with food details."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            ml.id as log_id,
            ml.portions,
            ml.meal_type,
            ml.logged_at,
            ml.notes,
            f.id as food_id,
            f.name,
            f.calories,
            f.protein,
            f.carbs,
            f.fats,
            f.serving_size,
            f.is_favorite
        FROM meal_logs ml
        JOIN foods f ON ml.food_id = f.id
        WHERE DATE(ml.logged_at) = ?
        ORDER BY ml.logged_at ASC
    """, (target_date.isoformat(),))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_meals_for_date_range(start_date: date, end_date: date) -> List[dict]:
    """Get all meals in a date range with food details."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            ml.id as log_id,
            ml.portions,
            ml.meal_type,
            ml.logged_at,
            ml.notes,
            f.id as food_id,
            f.name,
            f.calories,
            f.protein,
            f.carbs,
            f.fats,
            f.serving_size
        FROM meal_logs ml
        JOIN foods f ON ml.food_id = f.id
        WHERE DATE(ml.logged_at) BETWEEN ? AND ?
        ORDER BY ml.logged_at ASC
    """, (start_date.isoformat(), end_date.isoformat()))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_recent_foods(limit: int = 10) -> List[dict]:
    """Get recently logged foods for quick re-add."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT f.*
        FROM foods f
        JOIN meal_logs ml ON f.id = ml.food_id
        ORDER BY ml.logged_at DESC
        LIMIT ?
    """, (limit,))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


# ============== Settings Operations ==============

def get_setting(key: str, default: str = None) -> Optional[str]:
    """Get a setting value."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row['value'] if row else default


def set_setting(key: str, value: str):
    """Set a setting value."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
    """, (key, value))
    conn.commit()
    conn.close()


def get_all_settings() -> dict:
    """Get all settings as a dictionary."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    results = {row['key']: row['value'] for row in cursor.fetchall()}
    conn.close()
    return results


# ============== Off Days Operations ==============

OFF_DAY_REASONS = [
    'holiday',
    'weekend',
    'dinner with friends',
    'special date',
    'travel',
    'party',
    'other'
]


def add_off_day(target_date: date, reason: str, notes: str = None) -> int:
    """Add an off day. Returns the off day ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO off_days (date, reason, notes)
        VALUES (?, ?, ?)
    """, (target_date.isoformat(), reason, notes))
    off_day_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return off_day_id


def remove_off_day(target_date: date) -> bool:
    """Remove an off day. Returns True if successful."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM off_days WHERE date = ?", (target_date.isoformat(),))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def get_off_day(target_date: date) -> Optional[dict]:
    """Get off day info for a specific date."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM off_days WHERE date = ?", (target_date.isoformat(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_off_days_in_range(start_date: date, end_date: date) -> List[dict]:
    """Get all off days in a date range."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM off_days
        WHERE date BETWEEN ? AND ?
        ORDER BY date ASC
    """, (start_date.isoformat(), end_date.isoformat()))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def is_off_day(target_date: date) -> bool:
    """Check if a date is marked as an off day."""
    return get_off_day(target_date) is not None


# ============== Weight History Operations ==============

def log_weight(weight: float, recorded_at: date = None, notes: str = None) -> int:
    """Log a weight entry. Returns the entry ID."""
    if recorded_at is None:
        recorded_at = date.today()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO weight_history (weight, recorded_at, notes)
        VALUES (?, ?, ?)
    """, (weight, recorded_at.isoformat(), notes))
    entry_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return entry_id


def get_weight_history(limit: int = 30) -> List[dict]:
    """Get recent weight history entries."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM weight_history
        ORDER BY recorded_at DESC
        LIMIT ?
    """, (limit,))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_latest_weight() -> Optional[dict]:
    """Get the most recent weight entry."""
    history = get_weight_history(limit=1)
    return history[0] if history else None


# ============== Data Export/Import ==============

def export_data() -> dict:
    """Export all data as a dictionary for backup."""
    conn = get_connection()
    cursor = conn.cursor()

    data = {
        'foods': [],
        'meal_logs': [],
        'settings': {},
        'off_days': [],
        'weight_history': [],
        'exported_at': datetime.now().isoformat()
    }

    cursor.execute("SELECT * FROM foods")
    data['foods'] = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT * FROM meal_logs")
    data['meal_logs'] = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT key, value FROM settings")
    data['settings'] = {row['key']: row['value'] for row in cursor.fetchall()}

    cursor.execute("SELECT * FROM off_days")
    data['off_days'] = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT * FROM weight_history")
    data['weight_history'] = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return data


def import_data(data: dict, merge: bool = False):
    """Import data from a backup. If merge=False, clears existing data first."""
    conn = get_connection()
    cursor = conn.cursor()

    if not merge:
        cursor.execute("DELETE FROM meal_logs")
        cursor.execute("DELETE FROM foods")
        cursor.execute("DELETE FROM off_days")
        cursor.execute("DELETE FROM weight_history")

    # Import foods
    for food in data.get('foods', []):
        if merge:
            cursor.execute("""
                INSERT OR IGNORE INTO foods
                (id, name, calories, protein, carbs, fats, serving_size, is_favorite)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (food.get('id'), food['name'], food['calories'],
                  food.get('protein', 0), food.get('carbs', 0), food.get('fats', 0),
                  food.get('serving_size', '1 serving'), food.get('is_favorite', 0)))
        else:
            cursor.execute("""
                INSERT INTO foods
                (id, name, calories, protein, carbs, fats, serving_size, is_favorite)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (food.get('id'), food['name'], food['calories'],
                  food.get('protein', 0), food.get('carbs', 0), food.get('fats', 0),
                  food.get('serving_size', '1 serving'), food.get('is_favorite', 0)))

    # Import meal logs
    for log in data.get('meal_logs', []):
        if merge:
            cursor.execute("""
                INSERT OR IGNORE INTO meal_logs
                (id, food_id, portions, meal_type, logged_at, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (log.get('id'), log['food_id'], log['portions'],
                  log['meal_type'], log['logged_at'], log.get('notes')))
        else:
            cursor.execute("""
                INSERT INTO meal_logs
                (id, food_id, portions, meal_type, logged_at, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (log.get('id'), log['food_id'], log['portions'],
                  log['meal_type'], log['logged_at'], log.get('notes')))

    # Import settings
    for key, value in data.get('settings', {}).items():
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
        """, (key, value))

    # Import off days
    for off_day in data.get('off_days', []):
        cursor.execute("""
            INSERT OR REPLACE INTO off_days (date, reason, notes)
            VALUES (?, ?, ?)
        """, (off_day['date'], off_day['reason'], off_day.get('notes')))

    # Import weight history
    for entry in data.get('weight_history', []):
        cursor.execute("""
            INSERT OR REPLACE INTO weight_history (weight, recorded_at, notes)
            VALUES (?, ?, ?)
        """, (entry['weight'], entry['recorded_at'], entry.get('notes')))

    conn.commit()
    conn.close()


# ============== Multi-Ingredient Meal Operations ==============

def create_multi_meal(name: str, meal_type: str, ingredients: List[dict],
                      logged_at: datetime = None, notes: str = None) -> int:
    """
    Create a multi-ingredient meal.

    ingredients: List of dicts with keys:
        - food_id: int
        - amount_grams: float (amount in grams)

    Returns the meal ID.
    """
    if logged_at is None:
        logged_at = datetime.now()

    conn = get_connection()
    cursor = conn.cursor()

    # Calculate totals from ingredients
    total_calories = 0.0
    total_protein = 0.0
    total_carbs = 0.0
    total_fats = 0.0

    # Get food details and calculate nutrition for each ingredient
    ingredient_details = []
    for ing in ingredients:
        cursor.execute("SELECT * FROM foods WHERE id = ?", (ing['food_id'],))
        food = cursor.fetchone()
        if food:
            food = dict(food)
            amount = ing['amount_grams']
            # Calculate nutrition based on amount (foods are per 100g)
            multiplier = amount / 100.0
            cal = food['calories'] * multiplier
            pro = food['protein'] * multiplier
            carb = food['carbs'] * multiplier
            fat = food['fats'] * multiplier

            total_calories += cal
            total_protein += pro
            total_carbs += carb
            total_fats += fat

            ingredient_details.append({
                'food_id': ing['food_id'],
                'amount_grams': amount,
                'calories': cal,
                'protein': pro,
                'carbs': carb,
                'fats': fat
            })

    # Generate default name if not provided
    if not name:
        name = f"Meal at {logged_at.strftime('%I:%M %p')}"

    # Insert the meal
    cursor.execute("""
        INSERT INTO meals (name, meal_type, logged_at, total_calories, total_protein,
                          total_carbs, total_fats, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, meal_type, logged_at, total_calories, total_protein,
          total_carbs, total_fats, notes))

    meal_id = cursor.lastrowid

    # Insert all ingredients
    for ing in ingredient_details:
        cursor.execute("""
            INSERT INTO meal_ingredients (meal_id, food_id, amount_grams,
                                         calories, protein, carbs, fats)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (meal_id, ing['food_id'], ing['amount_grams'],
              ing['calories'], ing['protein'], ing['carbs'], ing['fats']))

    conn.commit()
    conn.close()
    return meal_id


def get_meal(meal_id: int) -> Optional[dict]:
    """Get a meal with all its ingredients."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM meals WHERE id = ?", (meal_id,))
    meal = cursor.fetchone()

    if not meal:
        conn.close()
        return None

    meal = dict(meal)

    # Get ingredients with food details
    cursor.execute("""
        SELECT
            mi.*,
            f.name as food_name,
            f.serving_size
        FROM meal_ingredients mi
        JOIN foods f ON mi.food_id = f.id
        WHERE mi.meal_id = ?
    """, (meal_id,))

    meal['ingredients'] = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return meal


def delete_multi_meal(meal_id: int) -> bool:
    """Delete a meal and all its ingredients."""
    conn = get_connection()
    cursor = conn.cursor()

    # Delete ingredients first (or rely on CASCADE)
    cursor.execute("DELETE FROM meal_ingredients WHERE meal_id = ?", (meal_id,))
    cursor.execute("DELETE FROM meals WHERE id = ?", (meal_id,))

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def get_multi_meals_for_date(target_date: date) -> List[dict]:
    """Get all multi-ingredient meals for a specific date."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM meals
        WHERE DATE(logged_at) = ?
        ORDER BY logged_at ASC
    """, (target_date.isoformat(),))

    meals = []
    for row in cursor.fetchall():
        meal = dict(row)

        # Get ingredients for this meal
        cursor.execute("""
            SELECT
                mi.*,
                f.name as food_name,
                f.serving_size
            FROM meal_ingredients mi
            JOIN foods f ON mi.food_id = f.id
            WHERE mi.meal_id = ?
        """, (meal['id'],))

        meal['ingredients'] = [dict(ing) for ing in cursor.fetchall()]
        meals.append(meal)

    conn.close()
    return meals


def get_all_meals_for_date(target_date: date) -> dict:
    """
    Get all meals for a date - both single-food logs and multi-ingredient meals.
    Returns a dict with 'single_logs' and 'multi_meals' keys.
    """
    single_logs = get_meals_for_date(target_date)
    multi_meals = get_multi_meals_for_date(target_date)

    return {
        'single_logs': single_logs,
        'multi_meals': multi_meals
    }


def get_multi_meals_for_date_range(start_date: date, end_date: date) -> List[dict]:
    """Get all multi-ingredient meals in a date range."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM meals
        WHERE DATE(logged_at) BETWEEN ? AND ?
        ORDER BY logged_at ASC
    """, (start_date.isoformat(), end_date.isoformat()))

    meals = []
    for row in cursor.fetchall():
        meal = dict(row)

        cursor.execute("""
            SELECT
                mi.*,
                f.name as food_name
            FROM meal_ingredients mi
            JOIN foods f ON mi.food_id = f.id
            WHERE mi.meal_id = ?
        """, (meal['id'],))

        meal['ingredients'] = [dict(ing) for ing in cursor.fetchall()]
        meals.append(meal)

    conn.close()
    return meals


# ============== Bulk Food Import ==============

def import_foods_bulk(foods_data: List[dict], skip_duplicates: bool = True) -> dict:
    """
    Import multiple foods at once.

    foods_data: List of dicts with keys: name, calories, protein, carbs, fats
    skip_duplicates: If True, skip foods that already exist. If False, update them.

    Returns dict with 'added', 'skipped', 'updated' counts.
    """
    conn = get_connection()
    cursor = conn.cursor()

    added = 0
    skipped = 0
    updated = 0

    for food in foods_data:
        name = food['name']
        calories = food.get('calories', 0)
        protein = food.get('protein', 0)
        carbs = food.get('carbs', 0)
        fats = food.get('fats', 0)
        serving_size = food.get('serving_size', '100g')

        # Check if food exists
        cursor.execute("SELECT id FROM foods WHERE name = ?", (name,))
        existing = cursor.fetchone()

        if existing:
            if skip_duplicates:
                skipped += 1
            else:
                # Update existing food
                cursor.execute("""
                    UPDATE foods
                    SET calories = ?, protein = ?, carbs = ?, fats = ?, serving_size = ?
                    WHERE name = ?
                """, (calories, protein, carbs, fats, serving_size, name))
                updated += 1
        else:
            cursor.execute("""
                INSERT INTO foods (name, calories, protein, carbs, fats, serving_size)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, calories, protein, carbs, fats, serving_size))
            added += 1

    conn.commit()
    conn.close()

    return {'added': added, 'skipped': skipped, 'updated': updated}
