from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class ParsedProduct:
    title: Optional[str]
    price_text: Optional[str]


def parse_product(site: str, html: str) -> ParsedProduct:
    soup = BeautifulSoup(html, "lxml")

    if site == "books_toscrape_home":
        first_book = soup.select_one("article.product_pod")
        if not first_book:
            return ParsedProduct(title=None, price_text=None)

        title_el = first_book.select_one("h3 a")
        price_el = first_book.select_one("p.price_color")
        return ParsedProduct(
            title=title_el.get("title") if title_el else None,
            price_text=price_el.get_text(strip=True) if price_el else None,
        )

    raise ValueError(f"Unknown site: {site}")
