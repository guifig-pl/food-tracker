#!/usr/bin/env python3
"""
Food Database Import Script

Imports a predefined set of foods into the Food Tracker database.
All nutritional values are per 100g unless otherwise specified.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

import database as db

# Food data: (name, calories, protein, carbs, fats)
# All values per 100g unless otherwise noted
FOODS_DATA = [
    # Protein products
    ("Müllermilch Protein Shake Schoko-Coco", 248, 26, 20.4, 6.8),
    ("Rewe Chocolate Protein Ice Cream", 132, 9.4, 17.7, 2.7),
    ("KADER Shake", 395, 59, 23, 8),
    ("Rewe Protein Bar ESN Dark Cookie", 178, 13, 12, 4),
    ("Vegan Shake", 138, 10, 10.6, 5.6),
    ("Protein Bowl", 86, 4.6, 12, 1.5),

    # Nuts and snacks
    ("Roasted Chickpeas", 279, 10, 32, 13),
    ("Peanuts Spicy", 590, 25, 16, 46),
    ("Salted Peanuts", 619, 24, 11, 51),
    ("Almonds", 576, 21, 22, 49),
    ("Cashews", 589, 20, 24, 45),
    ("BBQ Mix Nuts", 602, 26, 12, 48),
    ("Wasabi Peanuts", 402, 13, 62, 10),
    ("Kichererbsen Nuts Curry", 97, 4.3, 13, 3.2),

    # Fruits
    ("Banana", 108, 1.4, 28.8, 0.6),
    ("Strawberry", 32, 0.7, 7.7, 0.3),

    # Dairy
    ("Milk", 64, 3.3, 4.8, 3.5),
    ("Cheese", 300, 20, 0, 24),
    ("Frischkäse", 65, 13, 1, 0.8),

    # Beverages
    ("Coke (300ml)", 138.6, 0, 33, 0),

    # Sweets
    ("Goiabada", 324, 0, 81, 0),

    # Meats
    ("Chicken", 164, 31, 0, 3.5),
    ("Spiced Chicken", 209, 18, 0.5, 15),
    ("Chicken 2", 100, 21, 0.7, 1.5),
    ("Chicken w Bones", 129, 18, 3.3, 5.2),
    ("Chicken Heart", 185, 26, 0.1, 8),
    ("Donner Chicken", 204, 17.5, 5, 12),
    ("Spare Ribs", 243, 21, 5.8, 15),
    ("Spiced Pork", 181, 20, 0.5, 11),
    ("Black Angus Meat", 250, 25, 0, 15),
    ("Sausage", 350, 12, 1, 25),
    ("Bacon", 600, 35, 0, 40),
    ("Minced Meat", 280, 20, 0, 20),
    ("Strogonoff", 145, 12, 4, 9),

    # Fish
    ("Tuna Fish", 115, 26.6, 0, 0.9),

    # Eggs
    ("Egg", 60, 5, 0.4, 4),

    # Vegetables and sides
    ("Veggies", 47, 1.7, 4.4, 0.3),
    ("Butter Veggies", 92, 2.5, 6.8, 5.2),
    ("Chili Beans", 70, 3.9, 8.2, 0.8),
    ("Kichererbsen", 106, 7.5, 14, 0),

    # Carbs
    ("Baked Potato", 93, 2.5, 21, 0.1),
    ("Basmati Vollkorn", 140, 3.2, 28.8, 1),
    ("Mexican Rice", 92, 5.6, 13.6, 1.3),
    ("French Fries", 280, 3, 35, 12),
    ("Frozen Fries", 170, 2.5, 25, 6),
    ("Croquette", 170, 2.5, 25, 6),

    # Sauces and condiments
    ("Pesto Verde", 522, 4.5, 6.7, 44),

    # Fast food
    ("Five Guys", 610, 18, 39, 32),
]


def import_foods():
    """Import all foods into the database."""
    print("Food Tracker - Database Import")
    print("=" * 40)

    # Initialize database first
    db.init_database()

    # Convert to dict format
    foods_list = []
    for name, calories, protein, carbs, fats in FOODS_DATA:
        foods_list.append({
            'name': name,
            'calories': calories,
            'protein': protein,
            'carbs': carbs,
            'fats': fats,
            'serving_size': '100g'
        })

    print(f"Importing {len(foods_list)} foods...")

    # Import with skip_duplicates=True to avoid errors on re-run
    result = db.import_foods_bulk(foods_list, skip_duplicates=True)

    print(f"\nResults:")
    print(f"  Added:   {result['added']}")
    print(f"  Skipped: {result['skipped']} (already existed)")
    print(f"  Updated: {result['updated']}")

    # Show total foods in database
    all_foods = db.get_all_foods(limit=1000)
    print(f"\nTotal foods in database: {len(all_foods)}")

    return result


if __name__ == "__main__":
    import_foods()
