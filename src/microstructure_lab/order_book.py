from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OrderBook:
    tick_size: float
    bids: dict[float, float] = field(default_factory=dict)
    asks: dict[float, float] = field(default_factory=dict)

    def set_top(self, best_bid: float, bid_size: float, best_ask: float, ask_size: float) -> None:
        self.bids = {round(best_bid, 10): max(0.0, bid_size)}
        self.asks = {round(best_ask, 10): max(0.0, ask_size)}

    def update_level(self, side: str, price: float, size: float) -> None:
        book = self.bids if side == "bid" else self.asks
        key = round(price, 10)
        if size <= 0:
            book.pop(key, None)
            return
        book[key] = size

    def best_bid(self) -> float:
        if not self.bids:
            raise ValueError("No bids in book")
        return max(self.bids)

    def best_ask(self) -> float:
        if not self.asks:
            raise ValueError("No asks in book")
        return min(self.asks)

    def spread(self) -> float:
        return self.best_ask() - self.best_bid()

    def mid(self) -> float:
        return 0.5 * (self.best_bid() + self.best_ask())

    def imbalance(self) -> float:
        bid_sz = self.bids.get(self.best_bid(), 0.0)
        ask_sz = self.asks.get(self.best_ask(), 0.0)
        total = bid_sz + ask_sz
        if total <= 0:
            return 0.0
        return (bid_sz - ask_sz) / total
