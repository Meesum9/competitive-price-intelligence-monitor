"""Tests for the scraper module."""

import pytest
from unittest.mock import MagicMock, patch

import scraper


# ---------------------------------------------------------------------------
# _parse_price
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("$1,299.99",  1299.99),
    ("€ 1.299,99", 1299.99),
    ("1 299.99 £",  1299.99),
    ("9.99",        9.99),
    ("100",         100.0),
    ("$0.50",       0.50),
    (" £ 49.95 ",   49.95),
    ("1,000",       1000.0),
])
def test_parse_price_valid(raw, expected):
    assert scraper._parse_price(raw) == pytest.approx(expected, rel=1e-4)


@pytest.mark.parametrize("raw", ["", "N/A", "price", "---"])
def test_parse_price_invalid(raw):
    with pytest.raises(ValueError):
        scraper._parse_price(raw)


# ---------------------------------------------------------------------------
# scrape_price
# ---------------------------------------------------------------------------

def _mock_response(html: str, status: int = 200):
    response = MagicMock()
    response.status_code = status
    response.text = html
    response.raise_for_status = MagicMock()
    return response


def test_scrape_price_success():
    html = "<html><body><span class='price'>$29.99</span></body></html>"
    with patch("scraper.requests.Session") as MockSession:
        session = MockSession.return_value
        session.get.return_value = _mock_response(html)
        session.headers = {}
        price = scraper.scrape_price(
            "https://example.com/product",
            "span.price",
            session=session,
        )
    assert price == pytest.approx(29.99)


def test_scrape_price_selector_not_found():
    html = "<html><body><p>No price here</p></body></html>"
    with patch("scraper.requests.Session") as MockSession:
        session = MockSession.return_value
        session.get.return_value = _mock_response(html)
        session.headers = {}
        with pytest.raises(ValueError, match="matched nothing"):
            scraper.scrape_price(
                "https://example.com",
                "span.price",
                session=session,
            )


def test_scrape_price_network_error():
    import requests as req_lib
    with patch("scraper.requests.Session") as MockSession:
        session = MockSession.return_value
        session.headers = {}
        session.get.side_effect = req_lib.ConnectionError("unreachable")
        with pytest.raises(req_lib.ConnectionError):
            scraper.scrape_price("https://example.com", "span.price", session=session)


# ---------------------------------------------------------------------------
# scrape_all
# ---------------------------------------------------------------------------

def test_scrape_all_mixed_results():
    html_ok  = "<html><body><span class='price'>$10.00</span></body></html>"
    html_bad = "<html><body><p>No price</p></body></html>"

    products = [
        {"id": 1, "url": "https://ok.com",  "selector": "span.price"},
        {"id": 2, "url": "https://bad.com", "selector": "span.price"},
    ]

    responses = [_mock_response(html_ok), _mock_response(html_bad)]

    with patch("scraper.requests.Session") as MockSession:
        session = MockSession.return_value
        session.headers = {}
        session.get.side_effect = responses
        results = scraper.scrape_all(products, delay=0)

    assert results[1] == pytest.approx(10.0)
    assert isinstance(results[2], ValueError)
