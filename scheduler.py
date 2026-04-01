"""Periodic scraping scheduler.

Run this module directly to start the background scheduler::

    python scheduler.py

The scheduler scrapes all products every ``SCRAPE_INTERVAL_MINUTES`` minutes
(configured in config.py).  It can also be imported and the
``run_scrape_cycle()`` function called manually (e.g. from a Flask route or
a test).
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

import alerts
import config
import database as db
import scraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)


def run_scrape_cycle(db_path: str | None = None) -> dict:
    """Scrape all products once and process alerts.

    Returns a summary dict::

        {
            "scraped":  int,   # products successfully scraped
            "failed":   int,   # products that raised an exception
            "alerted":  int,   # products whose price triggered an alert
        }
    """
    products = db.get_all_products(db_path=db_path)
    if not products:
        logger.info("No products configured – nothing to scrape.")
        return {"scraped": 0, "failed": 0, "alerted": 0}

    product_list = [dict(p) for p in products]
    results = scraper.scrape_all(product_list)

    scraped = failed = alerted = 0
    for product in product_list:
        pid = product["id"]
        result = results.get(pid)
        if isinstance(result, Exception):
            failed += 1
            continue

        price: float = result
        alert = alerts.check_and_alert(pid, price, db_path=db_path)
        if alert:
            alerted += 1
        db.record_price(pid, price, db_path=db_path)
        scraped += 1

    logger.info(
        "Scrape cycle complete – scraped=%d  failed=%d  alerted=%d",
        scraped, failed, alerted,
    )
    return {"scraped": scraped, "failed": failed, "alerted": alerted}


def start_scheduler(db_path: str | None = None) -> BackgroundScheduler:
    """Start and return a background scheduler that runs ``run_scrape_cycle``
    every ``SCRAPE_INTERVAL_MINUTES`` minutes."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_scrape_cycle,
        trigger="interval",
        minutes=config.SCRAPE_INTERVAL_MINUTES,
        kwargs={"db_path": db_path},
        id="scrape_cycle",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started – scraping every %d minute(s).",
        config.SCRAPE_INTERVAL_MINUTES,
    )
    return scheduler


if __name__ == "__main__":
    db.init_db()
    start_scheduler()

    # Keep the process alive
    import time
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
