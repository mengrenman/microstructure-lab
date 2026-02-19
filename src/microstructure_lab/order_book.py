from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OrderBook:
    """Multi-level limit order book.

    Bids and asks are stored as ``{price: size}`` dicts.  Best bid is the
    *highest* bid price; best ask is the *lowest* ask price.  The book is
    intentionally kept simple (no queue-position tracking) while supporting
    genuine multi-level depth queries via :meth:`depth`.
    """

    tick_size: float
    bids: dict[float, float] = field(default_factory=dict)
    asks: dict[float, float] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Level management
    # ------------------------------------------------------------------

    def set_top(self, best_bid: float, bid_size: float, best_ask: float, ask_size: float) -> None:
        """Replace the entire book with a single top-of-book level each side."""
        self.bids = {round(best_bid, 10): max(0.0, bid_size)}
        self.asks = {round(best_ask, 10): max(0.0, ask_size)}

    def update_level(self, side: str, price: float, size: float) -> None:
        """Insert or remove a single price level.

        A *size* of zero (or negative) removes the level entirely.
        """
        book = self.bids if side == "bid" else self.asks
        key = round(price, 10)
        if size <= 0:
            book.pop(key, None)
            return
        book[key] = size

    def set_depth(
        self,
        bid_levels: list[tuple[float, float]],
        ask_levels: list[tuple[float, float]],
    ) -> None:
        """Replace the full book with multi-level snapshots.

        Args:
            bid_levels: List of ``(price, size)`` pairs, any order.
            ask_levels: List of ``(price, size)`` pairs, any order.
        """
        self.bids = {round(p, 10): max(0.0, s) for p, s in bid_levels if s > 0}
        self.asks = {round(p, 10): max(0.0, s) for p, s in ask_levels if s > 0}

    # ------------------------------------------------------------------
    # Best quotes
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Imbalance
    # ------------------------------------------------------------------

    def imbalance(self) -> float:
        """Signed top-of-book size imbalance in [-1, +1].

        Positive means more bid size than ask size (buying pressure).
        """
        bid_sz = self.bids.get(self.best_bid(), 0.0)
        ask_sz = self.asks.get(self.best_ask(), 0.0)
        total = bid_sz + ask_sz
        if total <= 0:
            return 0.0
        return (bid_sz - ask_sz) / total

    def weighted_mid(self) -> float:
        """Volume-weighted mid-price using top-of-book sizes."""
        bid_p = self.best_bid()
        ask_p = self.best_ask()
        bid_s = self.bids.get(bid_p, 0.0)
        ask_s = self.asks.get(ask_p, 0.0)
        total = bid_s + ask_s
        if total <= 0:
            return self.mid()
        return (bid_p * ask_s + ask_p * bid_s) / total

    # ------------------------------------------------------------------
    # Multi-level depth queries
    # ------------------------------------------------------------------

    def depth(self, n: int) -> dict[str, list[tuple[float, float]]]:
        """Return the top-*n* levels on each side.

        Returns a dict with keys ``"bids"`` and ``"asks"``, each containing a
        list of ``(price, size)`` tuples ordered from best to worst:

        * Bids: descending by price (highest first).
        * Asks: ascending by price (lowest first).

        If fewer than *n* levels exist the list is simply shorter.
        """
        bid_levels = sorted(self.bids.items(), key=lambda x: -x[0])[:n]
        ask_levels = sorted(self.asks.items(), key=lambda x: x[0])[:n]
        return {"bids": bid_levels, "asks": ask_levels}

    def total_bid_size(self, n: int | None = None) -> float:
        """Sum of sizes across the top-*n* bid levels (all levels if *n* is None)."""
        levels = sorted(self.bids.items(), key=lambda x: -x[0])
        if n is not None:
            levels = levels[:n]
        return sum(s for _, s in levels)

    def total_ask_size(self, n: int | None = None) -> float:
        """Sum of sizes across the top-*n* ask levels (all levels if *n* is None)."""
        levels = sorted(self.asks.items(), key=lambda x: x[0])
        if n is not None:
            levels = levels[:n]
        return sum(s for _, s in levels)

    def depth_imbalance(self, n: int = 5) -> float:
        """Signed size imbalance across the top-*n* levels on each side.

        Positive means more cumulative bid depth than ask depth.
        """
        bid_total = self.total_bid_size(n)
        ask_total = self.total_ask_size(n)
        total = bid_total + ask_total
        if total <= 0:
            return 0.0
        return (bid_total - ask_total) / total
