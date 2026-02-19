from __future__ import annotations

from dataclasses import dataclass

from microstructure_lab.strategies.base import Strategy
from microstructure_lab.types import MarketState, QuoteIntent


@dataclass
class InventorySkewMM(Strategy):
    half_spread_bps: float = 3.0
    inv_penalty_bps: float = 0.8
    quote_size: float = 1.0

    def on_tick(self, state: MarketState, inventory: float) -> QuoteIntent:
        half = state.mid * (self.half_spread_bps / 10_000.0)
        skew = state.mid * (self.inv_penalty_bps / 10_000.0) * inventory

        bid_px = max(0.0, state.mid - half - skew)
        ask_px = max(bid_px, state.mid + half - skew)

        return QuoteIntent(
            bid_px=bid_px,
            bid_sz=self.quote_size,
            ask_px=ask_px,
            ask_sz=self.quote_size,
        )
