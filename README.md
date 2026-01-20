# Food Tracker

A mobile-first Progressive Web App (PWA) for tracking meals, calories, and macronutrients.

## Features

### Core Tracking
- Log meals with food items, portions, and timestamps
- Track calories and macronutrients (protein, carbs, fats)
- Search previously logged foods
- Mark foods as favorites for quick access
- Visual progress indicators with circular macro charts

### Goal Management
- Three fitness goals: Bulking (+300 cal), Cutting (-500 cal), Maintenance
- Customizable daily calorie and macro targets
- Track weight progress over time

### Off Days
- Mark specific days as "off days" (not tracked)
- Categorize by reason: holiday, weekend, dinner with friends, special date, travel, party, other
- View off day counts in analytics

### Analytics & Dashboard
- Daily progress with visual progress bars
- Weekly and monthly average calories and macros
- Interactive charts using Chart.js
- Week-by-week and month-by-month breakdowns

### PWA Features
- Installable on mobile devices
- Offline support with service worker
- Dark mode support
- Pull-to-refresh on mobile
- Touch-friendly UI with 44px minimum tap targets

## Project Structure

```
food_tracker/
├── backend/
│   └── api.py              # Flask REST API
├── static/
│   ├── css/
│   │   └── style.css       # Mobile-first CSS
│   ├── js/
│   │   ├── app.js          # Main application JavaScript
│   │   └── sw.js           # Service Worker
│   ├── icons/              # PWA icons (need to be generated)
│   └── manifest.json       # PWA manifest
├── templates/
│   └── index.html          # Main HTML template
├── database.py             # SQLite database operations
├── logic.py                # Business logic and calculations
├── cli.py                  # CLI interface (original)
├── main.py                 # CLI entry point
├── requirements.txt        # Python dependencies
└── README.md
```

## Setup

### Prerequisites
- Python 3.8+
- pip

### Installation

1. Clone or navigate to the project directory:
```bash
cd food_tracker
```

2. Install Python dependencies:
```bash
pip3 install -r requirements.txt
pip3 install flask flask-cors
```

3. (Optional) Generate PWA icons:
```bash
# You can use any icon generator or create your own icons
# Place icons in static/icons/ with sizes: 72, 96, 128, 144, 152, 192, 384, 512
```

### Running the Application

#### Web Application (Recommended)
```bash
python3 backend/api.py
```

The app will be available at `http://localhost:5001`

> Note: Port 5001 is used because port 5000 is often occupied by AirPlay Receiver on macOS.

#### CLI Application
```bash
python3 main.py
```

## API Endpoints

### Foods
- `GET /api/foods` - Get all foods (with optional `?q=search` query)
- `GET /api/foods/<id>` - Get single food
- `POST /api/foods` - Add new food
- `PUT /api/foods/<id>` - Update food
- `DELETE /api/foods/<id>` - Delete food
- `POST /api/foods/<id>/favorite` - Toggle favorite
- `GET /api/foods/favorites` - Get favorite foods
- `GET /api/foods/recent` - Get recently logged foods

### Meals
- `GET /api/meals?date=YYYY-MM-DD` - Get meals for date
- `POST /api/meals` - Log a meal
- `DELETE /api/meals/<id>` - Delete meal log

### Progress
- `GET /api/progress/daily?date=YYYY-MM-DD` - Get daily progress
- `GET /api/progress/weekly` - Get weekly averages
- `GET /api/progress/monthly` - Get monthly averages
- `GET /api/analytics/breakdown` - Get week/month breakdown

### Settings
- `GET /api/settings` - Get all settings
- `PUT /api/settings` - Update settings
- `PUT /api/settings/goal` - Update fitness goal

### Off Days
- `GET /api/off-days` - Get off days
- `POST /api/off-days` - Add off day
- `DELETE /api/off-days/<date>` - Remove off day

### Weight
- `GET /api/weight` - Get weight history
- `POST /api/weight` - Log weight

### Data
- `GET /api/export` - Export all data as JSON
- `POST /api/import` - Import data from JSON

## Mobile Installation

### iOS (Safari)
1. Open `http://localhost:5001` in Safari
2. Tap the Share button
3. Select "Add to Home Screen"

### Android (Chrome)
1. Open `http://localhost:5001` in Chrome
2. Tap the menu (three dots)
3. Select "Add to Home screen" or look for the install prompt

## Technology Stack

- **Backend**: Python Flask with RESTful API
- **Frontend**: Vanilla JavaScript (no framework dependencies)
- **Database**: SQLite
- **Styling**: Custom CSS with CSS Variables
- **Charts**: Chart.js
- **PWA**: Service Worker + Web App Manifest

## Database

Data is stored in SQLite at `~/.food_tracker/food_tracker.db`

### Tables
- `foods` - Food items with nutritional info
- `meal_logs` - Logged meals
- `settings` - User settings and targets
- `off_days` - Off day records
- `weight_history` - Weight tracking

## Contributing

Feel free to submit issues and pull requests.

## License

MIT License
