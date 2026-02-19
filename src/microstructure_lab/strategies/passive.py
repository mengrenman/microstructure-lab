from __future__ import annotations

from dataclasses import dataclass

from microstructure_lab.strategies.base import Strategy
from microstructure_lab.types import MarketState, QuoteIntent


@dataclass
class DoNothingStrategy(Strategy):
    """Baseline strategy that never quotes.

    Useful as a control: any strategy's PnL should be compared against this
    to isolate the contribution of active trading versus simply holding zero
    inventory.  The "PnL" here will always be zero (no fills, no fees) which
    makes it easy to visualize fee drag from other strategies.
    """

    def on_tick(self, state: MarketState, inventory: float) -> QuoteIntent:
        return QuoteIntent(
            bid_px=0.0,
            bid_sz=0.0,
            ask_px=state.best_ask,
            ask_sz=0.0,
        )
