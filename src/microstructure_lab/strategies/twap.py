from __future__ import annotations

from dataclasses import dataclass

from microstructure_lab.strategies.base import Strategy
from microstructure_lab.types import MarketState, QuoteIntent


@dataclass
class TWAPStrategy(Strategy):
    """Time-Weighted Average Price execution strategy.

    Slices a target position into equal child orders distributed evenly over
    ``total_steps`` ticks.  Each child order is submitted as a passive limit
    quote at the current best bid/ask.  Once the target is reached the
    strategy quotes nothing.

    This contrasts with the market-maker: the MM earns spread by providing
    two-sided liquidity; TWAP consumes liquidity in one direction to reach a
    pre-defined inventory goal.

    Parameters
    ----------
    target_inventory:
        Signed target position (positive = long, negative = short).
    total_steps:
        Number of steps over which to distribute the order.
    quote_size:
        Maximum size of each child order.
    """

    target_inventory: float = 10.0
    total_steps: int = 200
    quote_size: float = 0.5

    def on_tick(self, state: MarketState, inventory: float) -> QuoteIntent:
        remaining = self.target_inventory - inventory
        # No more work to do.
        if abs(remaining) < 1e-9 or state.step >= self.total_steps:
            return QuoteIntent(bid_px=0.0, bid_sz=0.0, ask_px=state.best_ask, ask_sz=0.0)

        child_size = min(self.quote_size, abs(remaining))

        if remaining > 0:
            # Need to buy: place passive bid at best bid.
            return QuoteIntent(
                bid_px=state.best_bid,
                bid_sz=child_size,
                ask_px=state.best_ask,
                ask_sz=0.0,
            )
        else:
            # Need to sell: place passive ask at best ask.
            return QuoteIntent(
                bid_px=0.0,
                bid_sz=0.0,
                ask_px=state.best_ask,
                ask_sz=child_size,
            )
