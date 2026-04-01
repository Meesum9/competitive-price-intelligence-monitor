from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PriceDiff:
    product_id: str
    old_price: Optional[float]
    new_price: Optional[float]
    pct_change: Optional[float]


def compute_diff(product_id: str, old_price: Optional[float], new_price: Optional[float]) -> PriceDiff:
    if old_price is None or new_price is None:
        return PriceDiff(product_id=product_id, old_price=old_price, new_price=new_price, pct_change=None)

    if old_price == 0:
        return PriceDiff(product_id=product_id, old_price=old_price, new_price=new_price, pct_change=None)

    pct = ((new_price - old_price) / old_price) * 100.0
    return PriceDiff(product_id=product_id, old_price=old_price, new_price=new_price, pct_change=pct)


def should_alert(pct_change: Optional[float], pct_drop: float, pct_rise: float) -> bool:
    if pct_change is None:
        return False
    if pct_change <= -abs(pct_drop):
        return True
    if pct_change >= abs(pct_rise):
        return True
    return False
