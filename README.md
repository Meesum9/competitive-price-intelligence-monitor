# Competitive Price Intelligence Monitor

A small end-to-end **competitive price intelligence** project:

- **Scrape** product pages with `requests` + `BeautifulSoup`
- **Store** raw scrapes + time-series history in **SQLite**
- **Schedule** scraping with **APScheduler**
- **Detect** price changes (diff engine)
- **Alert** via webhook (optional)
- **Visualize** latest + history via a **Flask** dashboard

This repo ships with a safe default target: `http://books.toscrape.com/`.

## Project structure

```
price_monitor/
├── config.py
├── scraper/
│   ├── extractor.py
│   └── parser.py
├── storage/
│   ├── db.py
│   └── models.py
├── scheduler/
│   └── runner.py
├── intelligence/
│   ├── diff_engine.py
│   └── alerter.py
├── dashboard/
│   ├── app.py
│   └── templates/
│       └── index.html
├── data/
│   └── prices.db
└── requirements.txt
```

## Setup

From the `price_monitor/` directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configure targets

Edit `config.py`.

- `TARGETS`: list of products/pages to monitor
- `SCRAPE_INTERVAL_SECONDS`: scheduler interval
- `DB_PATH`: SQLite path (default `data/prices.db`)
- `ALERT_WEBHOOK_URL`: optional webhook endpoint

Example target:

```python
TARGETS = [
    {
        "product_id": "books_home_first",
        "site": "books_toscrape_home",
        "url": "http://books.toscrape.com/",
        "name": "Books to Scrape (first listing)",
        "currency": "GBP",
        "alert": {"pct_drop": 5.0, "pct_rise": 5.0},
    }
]
```

If you add a new site, implement its selectors in `scraper/parser.py`.

## Run: one-off scrape

```bash
python -m scraper.extractor
```

This will:

- create/update `data/prices.db`
- insert a row into `raw_prices`
- append a row into `price_history`

## Run: scheduler (continuous)

```bash
python -m scheduler.runner
```

Stop with `Ctrl+C`.

## Run: dashboard

```bash
python dashboard/app.py
```

Open:

- `http://127.0.0.1:5000/`

Click a product to view its price history chart.

## SQLite schema

To inspect the schema:

```bash
sqlite3 data/prices.db ".schema"
sqlite3 data/prices.db "PRAGMA table_info(raw_prices);"
```

## Notes / limitations

- This is a starter project.
- For production:
  - add retries/backoff, proxies, robots.txt compliance
  - implement per-site parsing rules
  - add richer alerting (Slack/email) and authentication for the dashboard
