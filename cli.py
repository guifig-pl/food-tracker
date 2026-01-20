"""
CLI Interface module for Food Tracker.
Handles all user interaction and display formatting.
"""

import sys
from datetime import date, datetime, timedelta
from typing import Optional, List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, FloatPrompt, Confirm
from rich.progress import Progress, BarColumn, TextColumn
from rich.layout import Layout
from rich.text import Text
from rich import box

import database as db
import logic

console = Console()


# ============== Helper Functions ==============

def clear_screen():
    """Clear the console screen."""
    console.clear()


def print_header(title: str):
    """Print a styled header."""
    console.print()
    console.print(Panel(f"[bold cyan]{title}[/bold cyan]", box=box.DOUBLE))
    console.print()


def print_success(message: str):
    """Print a success message."""
    console.print(f"[green]{message}[/green]")


def print_error(message: str):
    """Print an error message."""
    console.print(f"[red]Error: {message}[/red]")


def print_warning(message: str):
    """Print a warning message."""
    console.print(f"[yellow]{message}[/yellow]")


def press_enter_to_continue():
    """Wait for user to press Enter."""
    console.print()
    Prompt.ask("[dim]Press Enter to continue[/dim]")


def parse_date(date_str: str) -> Optional[date]:
    """Parse a date string. Returns None if invalid."""
    if not date_str or date_str.lower() == 'today':
        return date.today()
    if date_str.lower() == 'yesterday':
        return date.today() - timedelta(days=1)

    formats = ['%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%d/%m/%Y']
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def format_number(value: float, decimals: int = 1) -> str:
    """Format a number for display."""
    if decimals == 0:
        return f"{int(round(value)):,}"
    return f"{value:,.{decimals}f}"


# ============== Progress Bar Display ==============

def create_progress_bar(current: float, target: float, width: int = 30) -> str:
    """Create a text-based progress bar."""
    if target <= 0:
        return "[dim]No target set[/dim]"

    percentage = min(current / target, 1.5)  # Cap at 150% for display
    filled = int(percentage * width)
    filled = min(filled, width)

    if percentage >= 1.0:
        color = "green" if percentage <= 1.1 else "yellow"
    else:
        color = "blue"

    bar = f"[{color}]{'█' * filled}[/{color}][dim]{'░' * (width - filled)}[/dim]"
    pct_str = f"{percentage * 100:.0f}%"

    return f"{bar} {pct_str}"


# ============== Food Management ==============

def display_food_table(foods: List[dict], show_id: bool = True):
    """Display a table of foods."""
    if not foods:
        print_warning("No foods found.")
        return

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")

    if show_id:
        table.add_column("ID", style="dim", width=5)
    table.add_column("Name", style="cyan", min_width=20)
    table.add_column("Calories", justify="right")
    table.add_column("Protein", justify="right")
    table.add_column("Carbs", justify="right")
    table.add_column("Fats", justify="right")
    table.add_column("Serving", style="dim")
    table.add_column("Fav", justify="center")

    for food in foods:
        fav = "[yellow]★[/yellow]" if food['is_favorite'] else ""
        row = []
        if show_id:
            row.append(str(food['id']))
        row.extend([
            food['name'],
            format_number(food['calories'], 0),
            f"{format_number(food['protein'], 1)}g",
            f"{format_number(food['carbs'], 1)}g",
            f"{format_number(food['fats'], 1)}g",
            food.get('serving_size', '1 serving'),
            fav
        ])
        table.add_row(*row)

    console.print(table)


def add_food_menu():
    """Menu to add a new food."""
    print_header("Add New Food")

    name = Prompt.ask("Food name")
    if not name:
        print_error("Food name is required.")
        return

    # Check if food already exists
    existing = db.search_foods(name)
    if existing:
        exact_match = [f for f in existing if f['name'].lower() == name.lower()]
        if exact_match:
            print_warning(f"A food named '{name}' already exists.")
            if not Confirm.ask("Add anyway with a different name?"):
                return

    calories = FloatPrompt.ask("Calories per serving", default=0.0)
    protein = FloatPrompt.ask("Protein (g)", default=0.0)
    carbs = FloatPrompt.ask("Carbs (g)", default=0.0)
    fats = FloatPrompt.ask("Fats (g)", default=0.0)
    serving_size = Prompt.ask("Serving size", default="1 serving")

    try:
        food_id = db.add_food(name, calories, protein, carbs, fats, serving_size)
        print_success(f"Added '{name}' (ID: {food_id})")

        if Confirm.ask("Mark as favorite?", default=False):
            db.toggle_favorite(food_id)
            print_success("Marked as favorite!")
    except Exception as e:
        print_error(f"Failed to add food: {e}")


def search_foods_menu():
    """Menu to search and manage foods."""
    print_header("Search Foods")

    query = Prompt.ask("Search query (or 'all' for all foods)")

    if query.lower() == 'all':
        foods = db.get_all_foods()
    else:
        foods = db.search_foods(query)

    if not foods:
        print_warning("No foods found.")
        return

    display_food_table(foods)

    console.print()
    console.print("[dim]Actions: (e)dit, (d)elete, (f)avorite toggle, (Enter) to go back[/dim]")
    action = Prompt.ask("Action", default="")

    if action.lower() == 'e':
        food_id = IntPrompt.ask("Enter food ID to edit")
        edit_food_menu(food_id)
    elif action.lower() == 'd':
        food_id = IntPrompt.ask("Enter food ID to delete")
        if Confirm.ask(f"Are you sure you want to delete food {food_id}?"):
            if db.delete_food(food_id):
                print_success("Food deleted.")
            else:
                print_error("Food not found.")
    elif action.lower() == 'f':
        food_id = IntPrompt.ask("Enter food ID to toggle favorite")
        is_fav = db.toggle_favorite(food_id)
        print_success(f"Food {'marked as' if is_fav else 'removed from'} favorites.")


def edit_food_menu(food_id: int):
    """Edit an existing food."""
    food = db.get_food(food_id)
    if not food:
        print_error("Food not found.")
        return

    print_header(f"Edit Food: {food['name']}")

    console.print(f"Current values (press Enter to keep):")
    console.print(f"  Name: {food['name']}")
    console.print(f"  Calories: {food['calories']}")
    console.print(f"  Protein: {food['protein']}g")
    console.print(f"  Carbs: {food['carbs']}g")
    console.print(f"  Fats: {food['fats']}g")
    console.print(f"  Serving: {food['serving_size']}")
    console.print()

    name = Prompt.ask("New name", default=food['name'])
    calories = FloatPrompt.ask("Calories", default=food['calories'])
    protein = FloatPrompt.ask("Protein (g)", default=food['protein'])
    carbs = FloatPrompt.ask("Carbs (g)", default=food['carbs'])
    fats = FloatPrompt.ask("Fats (g)", default=food['fats'])
    serving_size = Prompt.ask("Serving size", default=food['serving_size'])

    if db.update_food(food_id, name, calories, protein, carbs, fats, serving_size):
        print_success("Food updated successfully.")
    else:
        print_error("Failed to update food.")


def view_favorites_menu():
    """View and manage favorite foods."""
    print_header("Favorite Foods")

    favorites = db.get_favorite_foods()
    if not favorites:
        print_warning("No favorite foods yet. Add foods and mark them as favorites!")
        return

    display_food_table(favorites)


# ============== Meal Logging ==============

def log_meal_menu():
    """Menu to log a meal."""
    print_header("Log Meal")

    console.print("How would you like to find the food?")
    console.print("  [1] Search by name")
    console.print("  [2] Recent foods")
    console.print("  [3] Favorites")
    console.print("  [4] Add new food first")
    console.print()

    choice = Prompt.ask("Choice", choices=["1", "2", "3", "4"], default="1")

    food = None

    if choice == "1":
        query = Prompt.ask("Search for food")
        foods = db.search_foods(query)
        if not foods:
            print_warning("No foods found. Would you like to add it?")
            if Confirm.ask("Add new food?"):
                add_food_menu()
            return
        display_food_table(foods)
        food_id = IntPrompt.ask("Select food ID")
        food = db.get_food(food_id)

    elif choice == "2":
        foods = db.get_recent_foods(10)
        if not foods:
            print_warning("No recent foods. Log some meals first!")
            return
        display_food_table(foods)
        food_id = IntPrompt.ask("Select food ID")
        food = db.get_food(food_id)

    elif choice == "3":
        foods = db.get_favorite_foods()
        if not foods:
            print_warning("No favorite foods yet.")
            return
        display_food_table(foods)
        food_id = IntPrompt.ask("Select food ID")
        food = db.get_food(food_id)

    elif choice == "4":
        add_food_menu()
        return

    if not food:
        print_error("Food not found.")
        return

    console.print()
    console.print(f"[cyan]Selected: {food['name']}[/cyan]")
    console.print(f"[dim]Per serving: {food['calories']} cal, "
                  f"{food['protein']}g protein, {food['carbs']}g carbs, {food['fats']}g fats[/dim]")
    console.print()

    portions = FloatPrompt.ask("Portions", default=1.0)

    console.print()
    console.print("Meal type:")
    for i, meal_type in enumerate(logic.MEAL_TYPES, 1):
        console.print(f"  [{i}] {meal_type.capitalize()}")

    meal_choice = Prompt.ask("Choice", choices=["1", "2", "3", "4"], default="1")
    meal_type = logic.MEAL_TYPES[int(meal_choice) - 1]

    date_str = Prompt.ask("Date (YYYY-MM-DD or 'today')", default="today")
    log_date = parse_date(date_str)
    if not log_date:
        print_error("Invalid date format.")
        return

    # Check if it's an off day
    if db.is_off_day(log_date):
        print_warning(f"{log_date} is marked as an off day.")
        if not Confirm.ask("Log meal anyway?"):
            return

    notes = Prompt.ask("Notes (optional)", default="")

    log_time = datetime.combine(log_date, datetime.now().time())

    try:
        log_id = db.log_meal(food['id'], portions, meal_type, log_time, notes or None)
        total_cals = food['calories'] * portions
        print_success(f"Logged {portions}x {food['name']} ({total_cals:.0f} cal) for {meal_type}")
    except Exception as e:
        print_error(f"Failed to log meal: {e}")


def view_today_meals():
    """View meals logged today."""
    view_meals_for_date(date.today())


def view_meals_for_date(target_date: date):
    """View meals for a specific date."""
    print_header(f"Meals for {target_date.strftime('%A, %B %d, %Y')}")

    if db.is_off_day(target_date):
        off_day = db.get_off_day(target_date)
        console.print(Panel(
            f"[yellow]OFF DAY[/yellow] - {off_day['reason'].capitalize()}",
            box=box.ROUNDED
        ))
        console.print()

    meals = db.get_meals_for_date(target_date)

    if not meals:
        print_warning("No meals logged for this date.")
        return

    # Group by meal type
    by_type = {}
    for meal in meals:
        mt = meal['meal_type']
        if mt not in by_type:
            by_type[mt] = []
        by_type[mt].append(meal)

    for meal_type in logic.MEAL_TYPES:
        if meal_type not in by_type:
            continue

        console.print(f"\n[bold]{meal_type.capitalize()}[/bold]")

        table = Table(box=box.SIMPLE, show_header=True, header_style="dim")
        table.add_column("ID", style="dim", width=5)
        table.add_column("Food", min_width=20)
        table.add_column("Portions", justify="right")
        table.add_column("Calories", justify="right")
        table.add_column("P/C/F", justify="right")

        meal_total = 0
        for meal in by_type[meal_type]:
            cals = meal['calories'] * meal['portions']
            meal_total += cals
            pcf = f"{meal['protein'] * meal['portions']:.0f}/{meal['carbs'] * meal['portions']:.0f}/{meal['fats'] * meal['portions']:.0f}"
            table.add_row(
                str(meal['log_id']),
                meal['name'],
                f"{meal['portions']:.1f}",
                f"{cals:.0f}",
                pcf
            )

        console.print(table)
        console.print(f"[dim]Subtotal: {meal_total:.0f} cal[/dim]")

    # Daily totals
    progress = logic.calculate_daily_progress(target_date)
    console.print()
    display_daily_summary(progress)

    console.print()
    console.print("[dim]Actions: (d)elete meal, (Enter) to go back[/dim]")
    action = Prompt.ask("Action", default="")

    if action.lower() == 'd':
        log_id = IntPrompt.ask("Enter meal log ID to delete")
        if Confirm.ask(f"Delete meal log {log_id}?"):
            if db.delete_meal_log(log_id):
                print_success("Meal deleted.")
            else:
                print_error("Meal log not found.")


def display_daily_summary(progress: dict):
    """Display daily progress summary with progress bars."""
    totals = progress['totals']
    targets = progress['targets']

    console.print(Panel("[bold]Daily Summary[/bold]", box=box.ROUNDED))

    # Calories
    cal_bar = create_progress_bar(totals['calories'], targets['calories'])
    console.print(f"Calories:  {format_number(totals['calories'], 0):>6} / {targets['calories']} {cal_bar}")

    # Protein
    pro_bar = create_progress_bar(totals['protein'], targets['protein'])
    console.print(f"Protein:   {format_number(totals['protein'], 1):>6}g / {targets['protein']}g {pro_bar}")

    # Carbs
    carb_bar = create_progress_bar(totals['carbs'], targets['carbs'])
    console.print(f"Carbs:     {format_number(totals['carbs'], 1):>6}g / {targets['carbs']}g {carb_bar}")

    # Fats
    fat_bar = create_progress_bar(totals['fats'], targets['fats'])
    console.print(f"Fats:      {format_number(totals['fats'], 1):>6}g / {targets['fats']}g {fat_bar}")

    console.print()

    # Deficit/Surplus
    diff = progress['deficit_surplus']
    if diff > 0:
        console.print(f"[yellow]Surplus: +{diff:.0f} calories[/yellow]")
    elif diff < 0:
        console.print(f"[green]Deficit: {diff:.0f} calories[/green]")
    else:
        console.print("[blue]On target![/blue]")


# ============== Dashboard ==============

def display_dashboard():
    """Display the main dashboard."""
    clear_screen()
    print_header("Food Tracker Dashboard")

    # Current goal
    goal = logic.get_current_goal()
    goal_info = logic.get_goal_info(goal)
    console.print(f"[bold]Current Goal:[/bold] {goal_info['name']} - {goal_info['description']}")
    console.print()

    # Today's progress
    today_progress = logic.calculate_daily_progress()
    console.print("[bold cyan]Today's Progress[/bold cyan]")
    if today_progress['is_off_day']:
        console.print("[yellow]Today is marked as an off day[/yellow]")
    display_daily_summary(today_progress)

    # Streak
    streak = logic.get_streak()
    if streak > 0:
        console.print(f"\n[green]Tracking streak: {streak} days[/green]")

    # Weekly summary
    console.print()
    console.print("[bold cyan]This Week[/bold cyan]")
    weekly = logic.calculate_weekly_averages()
    console.print(f"  Average Calories: {weekly['averages']['calories']:.0f} / day")
    console.print(f"  Average Protein:  {weekly['averages']['protein']:.1f}g / day")
    console.print(f"  Tracked Days:     {weekly['tracked_days']}")
    console.print(f"  Off Days:         {weekly['off_day_count']}")

    # Weight progress
    weight_progress = logic.calculate_weight_progress()
    if weight_progress['current_weight']:
        console.print()
        console.print("[bold cyan]Weight Progress[/bold cyan]")
        console.print(f"  Current: {weight_progress['current_weight']:.1f} lbs")
        if weight_progress['change'] is not None:
            change_str = f"+{weight_progress['change']:.1f}" if weight_progress['change'] > 0 else f"{weight_progress['change']:.1f}"
            console.print(f"  Change:  {change_str} lbs ({weight_progress['trend_direction']})")

    press_enter_to_continue()


# ============== Analytics ==============

def analytics_menu():
    """Analytics submenu."""
    while True:
        clear_screen()
        print_header("Analytics")

        console.print("  [1] Weekly Breakdown")
        console.print("  [2] Monthly Breakdown")
        console.print("  [3] View Specific Date")
        console.print("  [4] Weight History")
        console.print("  [5] Off Days Summary")
        console.print("  [0] Back to Main Menu")
        console.print()

        choice = Prompt.ask("Choice", choices=["0", "1", "2", "3", "4", "5"], default="0")

        if choice == "0":
            break
        elif choice == "1":
            display_weekly_breakdown()
        elif choice == "2":
            display_monthly_breakdown()
        elif choice == "3":
            date_str = Prompt.ask("Enter date (YYYY-MM-DD)")
            target = parse_date(date_str)
            if target:
                view_meals_for_date(target)
            else:
                print_error("Invalid date.")
                press_enter_to_continue()
        elif choice == "4":
            display_weight_history()
        elif choice == "5":
            display_off_days_summary()


def display_weekly_breakdown():
    """Display week-by-week breakdown."""
    print_header("Weekly Breakdown")

    weeks = logic.get_weekly_breakdown(4)

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Week", min_width=20)
    table.add_column("Avg Cal", justify="right")
    table.add_column("Avg Protein", justify="right")
    table.add_column("Avg Carbs", justify="right")
    table.add_column("Avg Fats", justify="right")
    table.add_column("Days", justify="center")
    table.add_column("Off", justify="center")

    for week in weeks:
        week_label = f"{week['week_start'].strftime('%b %d')} - {week['week_end'].strftime('%b %d')}"
        table.add_row(
            week_label,
            f"{week['averages']['calories']:.0f}",
            f"{week['averages']['protein']:.1f}g",
            f"{week['averages']['carbs']:.1f}g",
            f"{week['averages']['fats']:.1f}g",
            str(week['tracked_days']),
            str(week['off_day_count'])
        )

    console.print(table)
    press_enter_to_continue()


def display_monthly_breakdown():
    """Display month-by-month breakdown."""
    print_header("Monthly Breakdown")

    months = logic.get_monthly_breakdown(3)

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Month", min_width=15)
    table.add_column("Avg Cal", justify="right")
    table.add_column("Avg Protein", justify="right")
    table.add_column("Avg Carbs", justify="right")
    table.add_column("Avg Fats", justify="right")
    table.add_column("Days", justify="center")
    table.add_column("Off", justify="center")

    for month in months:
        table.add_row(
            month['month_name'],
            f"{month['averages']['calories']:.0f}",
            f"{month['averages']['protein']:.1f}g",
            f"{month['averages']['carbs']:.1f}g",
            f"{month['averages']['fats']:.1f}g",
            str(month['tracked_days']),
            str(month['off_day_count'])
        )

    console.print(table)
    press_enter_to_continue()


def display_weight_history():
    """Display weight history."""
    print_header("Weight History")

    history = db.get_weight_history(30)

    if not history:
        print_warning("No weight entries recorded.")
        if Confirm.ask("Log your weight now?"):
            log_weight_menu()
        return

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Date", min_width=12)
    table.add_column("Weight", justify="right")
    table.add_column("Change", justify="right")
    table.add_column("Notes")

    prev_weight = None
    for entry in reversed(history):
        change = ""
        if prev_weight is not None:
            diff = entry['weight'] - prev_weight
            if diff > 0:
                change = f"[red]+{diff:.1f}[/red]"
            elif diff < 0:
                change = f"[green]{diff:.1f}[/green]"

        table.add_row(
            entry['recorded_at'],
            f"{entry['weight']:.1f} lbs",
            change,
            entry.get('notes') or ""
        )
        prev_weight = entry['weight']

    console.print(table)
    press_enter_to_continue()


def display_off_days_summary():
    """Display summary of off days."""
    print_header("Off Days Summary")

    # This month
    month_start = logic.get_month_start()
    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1)
    month_end = next_month - timedelta(days=1)

    off_days = db.get_off_days_in_range(month_start, month_end)

    console.print(f"[bold]This Month ({month_start.strftime('%B %Y')})[/bold]")
    console.print(f"Total off days: {len(off_days)}")
    console.print()

    if off_days:
        # Group by reason
        by_reason = {}
        for od in off_days:
            reason = od['reason']
            if reason not in by_reason:
                by_reason[reason] = []
            by_reason[reason].append(od)

        table = Table(box=box.SIMPLE, show_header=True)
        table.add_column("Reason")
        table.add_column("Count", justify="right")
        table.add_column("Dates")

        for reason, days in by_reason.items():
            dates = ", ".join([d['date'] for d in days[:3]])
            if len(days) > 3:
                dates += f" (+{len(days) - 3} more)"
            table.add_row(reason.capitalize(), str(len(days)), dates)

        console.print(table)

    press_enter_to_continue()


# ============== Settings ==============

def settings_menu():
    """Settings submenu."""
    while True:
        clear_screen()
        print_header("Settings")

        settings = db.get_all_settings()
        goal = settings.get('goal_type', 'maintenance')
        goal_info = logic.get_goal_info(goal)

        console.print(f"[bold]Current Settings:[/bold]")
        console.print(f"  Goal: {goal_info['name']}")
        console.print(f"  Daily Calories: {settings.get('daily_calorie_target', '2000')}")
        console.print(f"  Protein Target: {settings.get('protein_target', '150')}g")
        console.print(f"  Carbs Target: {settings.get('carbs_target', '200')}g")
        console.print(f"  Fats Target: {settings.get('fats_target', '65')}g")
        console.print()

        console.print("  [1] Change Goal")
        console.print("  [2] Set Calorie Target")
        console.print("  [3] Set Macro Targets")
        console.print("  [4] Log Weight")
        console.print("  [5] Manage Off Days")
        console.print("  [6] Export Data")
        console.print("  [7] Import Data")
        console.print("  [0] Back to Main Menu")
        console.print()

        choice = Prompt.ask("Choice", choices=["0", "1", "2", "3", "4", "5", "6", "7"], default="0")

        if choice == "0":
            break
        elif choice == "1":
            change_goal_menu()
        elif choice == "2":
            set_calorie_target_menu()
        elif choice == "3":
            set_macro_targets_menu()
        elif choice == "4":
            log_weight_menu()
        elif choice == "5":
            manage_off_days_menu()
        elif choice == "6":
            export_data_menu()
        elif choice == "7":
            import_data_menu()


def change_goal_menu():
    """Change fitness goal."""
    print_header("Change Goal")

    console.print("Available goals:")
    for i, (key, info) in enumerate(logic.GOAL_TYPES.items(), 1):
        console.print(f"  [{i}] {info['name']}: {info['description']}")
        console.print(f"      Calorie adjustment: {info['calorie_modifier']:+d}")
        console.print()

    choice = Prompt.ask("Select goal", choices=["1", "2", "3"])
    goal_keys = list(logic.GOAL_TYPES.keys())
    selected = goal_keys[int(choice) - 1]

    logic.set_goal(selected)
    print_success(f"Goal set to {logic.GOAL_TYPES[selected]['name']}")

    if Confirm.ask("Would you like to adjust your calorie target based on this goal?"):
        base = IntPrompt.ask("Enter your maintenance calories", default=2000)
        new_target = logic.calculate_recommended_calories(base)
        logic.set_daily_targets(calories=new_target)
        print_success(f"Calorie target set to {new_target}")

    press_enter_to_continue()


def set_calorie_target_menu():
    """Set daily calorie target."""
    current = int(db.get_setting('daily_calorie_target', '2000'))
    new_target = IntPrompt.ask("Daily calorie target", default=current)
    logic.set_daily_targets(calories=new_target)
    print_success(f"Daily calorie target set to {new_target}")
    press_enter_to_continue()


def set_macro_targets_menu():
    """Set macro targets."""
    print_header("Set Macro Targets")

    current_protein = int(db.get_setting('protein_target', '150'))
    current_carbs = int(db.get_setting('carbs_target', '200'))
    current_fats = int(db.get_setting('fats_target', '65'))

    protein = IntPrompt.ask("Protein target (g)", default=current_protein)
    carbs = IntPrompt.ask("Carbs target (g)", default=current_carbs)
    fats = IntPrompt.ask("Fats target (g)", default=current_fats)

    logic.set_daily_targets(protein=protein, carbs=carbs, fats=fats)

    # Show calculated calories from macros
    calc_cals = (protein * 4) + (carbs * 4) + (fats * 9)
    console.print(f"\n[dim]Note: These macros = ~{calc_cals} calories[/dim]")

    print_success("Macro targets updated!")
    press_enter_to_continue()


def log_weight_menu():
    """Log weight entry."""
    print_header("Log Weight")

    weight = FloatPrompt.ask("Weight (lbs)")
    date_str = Prompt.ask("Date (YYYY-MM-DD or 'today')", default="today")
    record_date = parse_date(date_str)
    if not record_date:
        print_error("Invalid date.")
        return

    notes = Prompt.ask("Notes (optional)", default="")

    db.log_weight(weight, record_date, notes or None)
    print_success(f"Logged weight: {weight} lbs for {record_date}")
    press_enter_to_continue()


def manage_off_days_menu():
    """Manage off days."""
    while True:
        clear_screen()
        print_header("Manage Off Days")

        console.print("  [1] Mark today as off day")
        console.print("  [2] Mark another date as off day")
        console.print("  [3] Remove off day")
        console.print("  [4] View off days this month")
        console.print("  [0] Back")
        console.print()

        choice = Prompt.ask("Choice", choices=["0", "1", "2", "3", "4"], default="0")

        if choice == "0":
            break
        elif choice == "1":
            add_off_day_for_date(date.today())
        elif choice == "2":
            date_str = Prompt.ask("Enter date (YYYY-MM-DD)")
            target = parse_date(date_str)
            if target:
                add_off_day_for_date(target)
            else:
                print_error("Invalid date.")
                press_enter_to_continue()
        elif choice == "3":
            date_str = Prompt.ask("Enter date to remove (YYYY-MM-DD)")
            target = parse_date(date_str)
            if target:
                if db.remove_off_day(target):
                    print_success(f"Off day removed for {target}")
                else:
                    print_error("No off day found for that date.")
                press_enter_to_continue()
            else:
                print_error("Invalid date.")
                press_enter_to_continue()
        elif choice == "4":
            display_off_days_summary()


def add_off_day_for_date(target_date: date):
    """Add an off day with reason selection."""
    console.print(f"\nMarking {target_date} as off day")
    console.print("\nReason:")
    for i, reason in enumerate(db.OFF_DAY_REASONS, 1):
        console.print(f"  [{i}] {reason.capitalize()}")

    choice = Prompt.ask("Select reason", choices=[str(i) for i in range(1, len(db.OFF_DAY_REASONS) + 1)])
    reason = db.OFF_DAY_REASONS[int(choice) - 1]

    notes = ""
    if reason == "other":
        notes = Prompt.ask("Describe the reason")

    db.add_off_day(target_date, reason, notes or None)
    print_success(f"Marked {target_date} as off day ({reason})")
    press_enter_to_continue()


# ============== Data Export/Import ==============

def export_data_menu():
    """Export data to JSON file."""
    import json
    from pathlib import Path

    print_header("Export Data")

    default_path = Path.home() / "food_tracker_backup.json"
    path_str = Prompt.ask("Export path", default=str(default_path))
    path = Path(path_str)

    try:
        data = db.export_data()
        with open(path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print_success(f"Data exported to {path}")
        console.print(f"  Foods: {len(data['foods'])}")
        console.print(f"  Meal logs: {len(data['meal_logs'])}")
        console.print(f"  Off days: {len(data['off_days'])}")
        console.print(f"  Weight entries: {len(data['weight_history'])}")
    except Exception as e:
        print_error(f"Export failed: {e}")

    press_enter_to_continue()


def import_data_menu():
    """Import data from JSON file."""
    import json
    from pathlib import Path

    print_header("Import Data")

    default_path = Path.home() / "food_tracker_backup.json"
    path_str = Prompt.ask("Import path", default=str(default_path))
    path = Path(path_str)

    if not path.exists():
        print_error(f"File not found: {path}")
        press_enter_to_continue()
        return

    try:
        with open(path, 'r') as f:
            data = json.load(f)

        console.print(f"\nFile contains:")
        console.print(f"  Foods: {len(data.get('foods', []))}")
        console.print(f"  Meal logs: {len(data.get('meal_logs', []))}")
        console.print(f"  Off days: {len(data.get('off_days', []))}")
        console.print(f"  Weight entries: {len(data.get('weight_history', []))}")
        console.print(f"  Exported at: {data.get('exported_at', 'Unknown')}")
        console.print()

        console.print("Import mode:")
        console.print("  [1] Replace all data (clears existing)")
        console.print("  [2] Merge with existing data")

        mode = Prompt.ask("Choice", choices=["1", "2"], default="2")
        merge = mode == "2"

        if not merge:
            if not Confirm.ask("[red]This will DELETE all existing data. Continue?[/red]"):
                return

        db.import_data(data, merge=merge)
        print_success("Data imported successfully!")

    except json.JSONDecodeError:
        print_error("Invalid JSON file.")
    except Exception as e:
        print_error(f"Import failed: {e}")

    press_enter_to_continue()


# ============== Main Menu ==============

def main_menu():
    """Display and handle main menu."""
    while True:
        clear_screen()
        console.print(Panel(
            "[bold cyan]Food Tracker[/bold cyan]\n[dim]Track your nutrition and reach your goals[/dim]",
            box=box.DOUBLE
        ))

        # Quick stats
        progress = logic.calculate_daily_progress()
        cals = progress['totals']['calories']
        target = progress['targets']['calories']
        console.print(f"[dim]Today: {cals:.0f} / {target} calories ({progress['percentage']['calories']:.0f}%)[/dim]")
        console.print()

        console.print("  [1] Log Meal")
        console.print("  [2] View Today's Meals")
        console.print("  [3] Dashboard")
        console.print("  [4] Analytics")
        console.print("  [5] Manage Foods")
        console.print("  [6] Quick Add (Favorites)")
        console.print("  [7] Settings")
        console.print("  [0] Exit")
        console.print()

        choice = Prompt.ask("Choice", choices=["0", "1", "2", "3", "4", "5", "6", "7"], default="1")

        if choice == "0":
            console.print("[cyan]Goodbye! Keep tracking![/cyan]")
            break
        elif choice == "1":
            log_meal_menu()
        elif choice == "2":
            view_today_meals()
            press_enter_to_continue()
        elif choice == "3":
            display_dashboard()
        elif choice == "4":
            analytics_menu()
        elif choice == "5":
            foods_menu()
        elif choice == "6":
            quick_add_menu()
        elif choice == "7":
            settings_menu()


def foods_menu():
    """Foods management submenu."""
    while True:
        clear_screen()
        print_header("Manage Foods")

        console.print("  [1] Add New Food")
        console.print("  [2] Search Foods")
        console.print("  [3] View Favorites")
        console.print("  [4] Recent Foods")
        console.print("  [0] Back")
        console.print()

        choice = Prompt.ask("Choice", choices=["0", "1", "2", "3", "4"], default="0")

        if choice == "0":
            break
        elif choice == "1":
            add_food_menu()
            press_enter_to_continue()
        elif choice == "2":
            search_foods_menu()
            press_enter_to_continue()
        elif choice == "3":
            view_favorites_menu()
            press_enter_to_continue()
        elif choice == "4":
            foods = db.get_recent_foods(20)
            display_food_table(foods)
            press_enter_to_continue()


def quick_add_menu():
    """Quick add from favorites."""
    print_header("Quick Add from Favorites")

    favorites = db.get_favorite_foods()
    if not favorites:
        print_warning("No favorites yet! Add foods and mark them as favorites for quick access.")
        press_enter_to_continue()
        return

    display_food_table(favorites)

    food_id = IntPrompt.ask("\nSelect food ID (0 to cancel)", default=0)
    if food_id == 0:
        return

    food = db.get_food(food_id)
    if not food:
        print_error("Food not found.")
        press_enter_to_continue()
        return

    portions = FloatPrompt.ask("Portions", default=1.0)

    console.print("\nMeal type:")
    for i, meal_type in enumerate(logic.MEAL_TYPES, 1):
        console.print(f"  [{i}] {meal_type.capitalize()}")

    meal_choice = Prompt.ask("Choice", choices=["1", "2", "3", "4"], default="1")
    meal_type = logic.MEAL_TYPES[int(meal_choice) - 1]

    try:
        db.log_meal(food['id'], portions, meal_type)
        total_cals = food['calories'] * portions
        print_success(f"Logged {portions}x {food['name']} ({total_cals:.0f} cal)")
    except Exception as e:
        print_error(f"Failed to log: {e}")

    press_enter_to_continue()


def run():
    """Entry point for the CLI."""
    try:
        db.init_database()
        main_menu()
    except KeyboardInterrupt:
        console.print("\n[cyan]Goodbye![/cyan]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Fatal error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    run()
