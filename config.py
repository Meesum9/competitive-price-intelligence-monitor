"""Central configuration for the price intelligence monitor."""

import os

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASE_PATH = os.environ.get("DB_PATH", "prices.db")

# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------
# Seconds to wait between HTTP requests (be polite to servers)
REQUEST_DELAY = float(os.environ.get("REQUEST_DELAY", "1.5"))
# Timeout for each HTTP request (seconds)
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "15"))
# User-agent sent with every request
USER_AGENT = (
    "Mozilla/5.0 (compatible; PriceBot/1.0; "
    "+https://github.com/Meesum9/competitive-price-intelligence-monitor)"
)

# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------
# Minimum absolute price change (in the product's currency) that triggers an alert
ALERT_MIN_CHANGE = float(os.environ.get("ALERT_MIN_CHANGE", "0.01"))
# Minimum *percentage* change (0–100) that triggers an alert
ALERT_THRESHOLD_PCT = float(os.environ.get("ALERT_THRESHOLD_PCT", "1.0"))

# --- Email alerts (optional) ---
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
ALERT_FROM = os.environ.get("ALERT_FROM", SMTP_USER)
ALERT_TO = os.environ.get("ALERT_TO", "")  # comma-separated list

# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
# How often to run the scraper, in minutes
SCRAPE_INTERVAL_MINUTES = int(os.environ.get("SCRAPE_INTERVAL_MINUTES", "60"))

# ---------------------------------------------------------------------------
# Flask
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
HOST = os.environ.get("FLASK_HOST", "127.0.0.1")
PORT = int(os.environ.get("FLASK_PORT", "5000"))
