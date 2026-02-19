from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MarketState:
    step: int
    mid: float
    best_bid: float
    best_ask: float
    spread: float
    imbalance: float
    volatility: float


@dataclass
class QuoteIntent:
    bid_px: float
    bid_sz: float
    ask_px: float
    ask_sz: float


@dataclass
class Fill:
    side: str
    price: float
    size: float
    fee: float
    step: int
