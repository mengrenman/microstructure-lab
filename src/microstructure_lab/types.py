from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict


class MarketEvent(TypedDict, total=False):
    """Typed contract for events emitted by :meth:`SyntheticScenario.stream`.

    Fields are optional (``total=False``) because depth-level keys are only
    present when ``depth_levels > 1``.
    """

    step: int
    mid: float
    best_bid: float
    best_ask: float
    # Top-of-book sizes — present when depth_levels == 1
    bid_size: float
    ask_size: float
    # Multi-level depth lists — present when depth_levels > 1
    bid_levels: list
    ask_levels: list
    volatility: float
    regime: str


@dataclass
class MarketState:
    step: int
    mid: float
    best_bid: float
    best_ask: float
    spread: float
    imbalance: float
    volatility: float
    # Regime label injected by the scenario generator (e.g. "calm" / "stressed").
    regime: str = "calm"


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
    # Adverse-selection fields: set post-hoc by the engine once future mid is known.
    # ``mid_before`` is the mid at fill time; ``mid_after`` is the mid k steps later.
    mid_before: float = 0.0
    mid_after: float = 0.0

    @property
    def adverse_selection_cost(self) -> float:
        """Signed adverse-selection cost per unit.

        For a passive *buy* fill, adverse selection is negative mid drift
        (mid falls after we buy).  For a passive *sell* fill, it is positive
        mid drift (mid rises after we sell).

        A negative value means the fill was adversely selected (bad for us).
        A positive value means we captured beneficial flow.
        """
        if self.side == "buy":
            return self.mid_after - self.mid_before
        return self.mid_before - self.mid_after

    @property
    def realized_spread(self) -> float:
        """Realized half-spread: what we actually captured net of adverse selection.

        For a maker *buy*:  fill_price - mid_after  (we paid fill_price, mid moved to mid_after)
        For a maker *sell*: mid_after - fill_price
        """
        if self.side == "buy":
            return self.mid_after - self.price
        return self.price - self.mid_after

    @property
    def quoted_spread_half(self) -> float:
        """Quoted half-spread at fill time (mid_before - fill_price for buys)."""
        if self.side == "buy":
            return self.mid_before - self.price
        return self.price - self.mid_before
