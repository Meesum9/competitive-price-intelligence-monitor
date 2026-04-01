# Competitive Price Intelligence Monitor

A self-hosted tool that scrapes product page prices, stores a full history in SQLite, triggers configurable change alerts, and serves a live Flask dashboard.

---

## Features

| Feature | Details |
|---|---|
| **Web scraper** | Fetches any product page and extracts the price using a user-supplied CSS selector. Handles `$`, `€`, `£` and both US / European number formats. |
| **Price history** | Every scraped price is persisted in a local SQLite database (`prices.db`). |
| **Change alerts** | When a price moves by more than the configured threshold (default 1 %), an alert record is created. Optional email delivery via SMTP. |
| **Scheduler** | A background APScheduler job re-scrapes all products at a configurable interval (default 60 minutes). |
| **Flask dashboard** | A browser UI to add / edit / delete products, view price history with a canvas chart, browse and acknowledge alerts, and trigger an on-demand scrape. |

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the dashboard (also initialises the database)
python app.py

# 3. Open http://127.0.0.1:5000 in your browser

# (optional) Run the standalone scheduler instead of the Flask dev server
python scheduler.py
```

---

## Configuration

All settings can be overridden with environment variables:

| Variable | Default | Description |
|---|---|---|
| `DB_PATH` | `prices.db` | Path to the SQLite database file |
| `SCRAPE_INTERVAL_MINUTES` | `60` | How often the scheduler re-scrapes all products |
| `ALERT_THRESHOLD_PCT` | `1.0` | Minimum price change (%) before an alert fires |
| `ALERT_MIN_CHANGE` | `0.01` | Minimum absolute change before an alert fires |
| `SMTP_HOST` | *(empty)* | SMTP server for email alerts |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | *(empty)* | SMTP username |
| `SMTP_PASSWORD` | *(empty)* | SMTP password |
| `ALERT_FROM` | same as `SMTP_USER` | Sender address for alert emails |
| `ALERT_TO` | *(empty)* | Comma-separated recipient addresses |
| `FLASK_HOST` | `127.0.0.1` | Flask bind host |
| `FLASK_PORT` | `5000` | Flask port |
| `FLASK_DEBUG` | `false` | Enable Flask debug mode |
| `SECRET_KEY` | `change-me-in-production` | Flask session secret key |

---

## Project Layout

```
.
├── app.py          # Flask dashboard
├── scraper.py      # Web scraping & price extraction
├── database.py     # SQLite schema & query helpers
├── alerts.py       # Price-change detection & email delivery
├── scheduler.py    # APScheduler background loop
├── config.py       # Central configuration
├── products.json   # Sample product list
├── requirements.txt
├── templates/      # Jinja2 HTML templates
│   ├── base.html
│   ├── index.html         # Product list
│   ├── product.html       # Product detail + price chart
│   ├── alerts.html        # Alert history
│   ├── add_product.html
│   └── edit_product.html
├── static/
│   └── style.css
└── tests/
    ├── test_database.py
    ├── test_scraper.py
    ├── test_alerts.py
    ├── test_scheduler.py
    └── test_app.py
```

---

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## Adding a Product via the UI

1. Click **+ Add Product** in the top navigation bar.
2. Enter the product name, URL, and the CSS selector that targets the price element on that page.
   - Example selector for [books.toscrape.com](https://books.toscrape.com): `p.price_color`
3. Click **Add Product**.  The next scheduled scrape (or a manual **Scrape Now**) will populate the price history.

---

## Seeding Sample Data from `products.json`

```python
import json, database as db

db.init_db()
with open("products.json") as f:
    for p in json.load(f):
        db.add_product(p["name"], p["url"], p["selector"])
```
