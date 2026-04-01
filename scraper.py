"""Web scraper for extracting product prices.

Each product is configured with:
  - url      : the product page URL
  - selector : a CSS selector that uniquely identifies the price element

The scraper strips currency symbols and thousands-separators, then parses
the remaining text as a float.
"""

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)

# Characters that are never part of a numeric price value
_CURRENCY_RE = re.compile(r"[^\d.,]")
# Normalise European-style decimals  (1.234,56 → 1234.56)
_EU_DECIMAL_RE = re.compile(r"^(\d{1,3}(?:\.\d{3})*),(\d{2})$")


def _parse_price(raw: str) -> float:
    """Extract a float price from raw text scraped from a page.

    Handles:
        "$1,299.99"  →  1299.99
        "€ 1.299,99" →  1299.99
        "1 299.99 £" →  1299.99
    """
    text = raw.strip()
    # Remove whitespace inside the number (e.g. "1 299")
    text = re.sub(r"\s+", "", text)
    # Strip everything that is not a digit, dot, or comma
    text = _CURRENCY_RE.sub("", text)
    if not text:
        raise ValueError(f"No numeric content found in: {raw!r}")

    # European format: "1.299,99"
    eu_match = _EU_DECIMAL_RE.match(text)
    if eu_match:
        text = eu_match.group(1).replace(".", "") + "." + eu_match.group(2)
        return float(text)

    # US/international format: "1,299.99" – remove thousands commas
    if text.count(".") <= 1 and "," in text:
        text = text.replace(",", "")

    return float(text)


def _build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": config.USER_AGENT})
    return session


def scrape_price(url: str, selector: str,
                 session: requests.Session | None = None) -> float:
    """Fetch *url* and extract the price using the CSS *selector*.

    Returns the price as a float.
    Raises ``ValueError`` if the selector matches nothing or the text cannot
    be parsed as a number.
    Raises ``requests.RequestException`` on network errors.
    """
    _session = session or _build_session()
    logger.info("Scraping %s", url)
    response = _session.get(url, timeout=config.REQUEST_TIMEOUT)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    element = soup.select_one(selector)
    if element is None:
        raise ValueError(
            f"CSS selector {selector!r} matched nothing on {url}"
        )
    raw_text = element.get_text()
    price = _parse_price(raw_text)
    logger.info("  → price = %.2f", price)
    return price


def scrape_all(products: list[dict], delay: float = config.REQUEST_DELAY) -> dict[int, float | Exception]:
    """Scrape prices for a list of product dicts.

    Each dict must have keys: ``id``, ``url``, ``selector``.

    Returns a mapping of ``product_id → price`` (or ``product_id → Exception``
    when scraping fails for that product).
    """
    session = _build_session()
    results: dict[int, float | Exception] = {}
    for i, product in enumerate(products):
        if i > 0:
            time.sleep(delay)
        try:
            price = scrape_price(product["url"], product["selector"], session=session)
            results[product["id"]] = price
        except Exception as exc:
            logger.warning("Failed to scrape product %s: %s", product["id"], exc)
            results[product["id"]] = exc
    return results
