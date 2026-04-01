from __future__ import annotations

import time

from apscheduler.schedulers.background import BackgroundScheduler

import config
from scraper.extractor import run_scrape_once
from storage.db import init_db


def main() -> None:
    init_db(config.DB_PATH)

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_scrape_once,
        "interval",
        seconds=config.SCRAPE_INTERVAL_SECONDS,
        id="price_monitor_scrape",
        max_instances=1,
        replace_existing=True,
    )
    scheduler.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
