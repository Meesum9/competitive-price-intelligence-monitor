# Phase 1: Configuration

SCRAPE_INTERVAL_SECONDS = 60

DB_PATH = "data/prices.db"

DEFAULT_CURRENCY = "GBP"

TARGETS = [
    {
        "product_id": "books_home_first",
        "site": "books_toscrape_home",
        "url": "http://books.toscrape.com/",
        "name": "Books to Scrape (first listing)",
        "currency": "GBP",
        "alert": {
            "pct_drop": 5.0,
            "pct_rise": 5.0,
        },
    }
]

ALERT_WEBHOOK_URL = None