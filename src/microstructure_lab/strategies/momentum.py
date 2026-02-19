from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from microstructure_lab.strategies.base import Strategy
from microstructure_lab.types import MarketState, QuoteIntent


@dataclass
class MomentumStrategy(Strategy):
    """Simple price-momentum directional strategy.

    Tracks a rolling window of mid-price returns.  When the average return
    over the window exceeds ``entry_threshold_bps`` the strategy buys
    (bullish momentum); when it falls below ``-entry_threshold_bps`` it
    sells (bearish momentum).  Otherwise it stays flat.

    Quotes are placed *aggressively* (at the opposite touch) so fills occur
    as taker trades — this intentionally incurs taker fees and demonstrates
    the fee drag of directional trading versus passive market-making.

    Parameters
    ----------
    window:
        Number of steps to compute the momentum signal.
    entry_threshold_bps:
        Signal must exceed this level (in basis points) to trigger a trade.
    quote_size:
        Size of each directional order.
    """

    window: int = 20
    entry_threshold_bps: float = 1.0
    quote_size: float = 1.0
    _mid_history: deque = field(default_factory=deque, init=False, repr=False)

    def __post_init__(self):
        self._mid_history = deque(maxlen=self.window)

    def on_tick(self, state: MarketState, inventory: float) -> QuoteIntent:
        self._mid_history.append(state.mid)

        if len(self._mid_history) < self.window:
            # Not enough history — sit flat with no quotes.
            return QuoteIntent(bid_px=0.0, bid_sz=0.0, ask_px=state.best_ask, ask_sz=0.0)

        mids = list(self._mid_history)
        # Average log return over the window (bps).
        avg_return_bps = ((mids[-1] / mids[0]) - 1.0) * 10_000.0

        if avg_return_bps > self.entry_threshold_bps:
            # Bullish: buy aggressively at best ask.
            return QuoteIntent(
                bid_px=state.best_ask,
                bid_sz=self.quote_size,
                ask_px=state.best_ask * 10.0,
                ask_sz=0.0,
            )
        elif avg_return_bps < -self.entry_threshold_bps:
            # Bearish: sell aggressively at best bid.
            return QuoteIntent(
                bid_px=0.0,
                bid_sz=0.0,
                ask_px=state.best_bid,
                ask_sz=self.quote_size,
            )
        else:
            # Flat signal — no quote.
            return QuoteIntent(bid_px=0.0, bid_sz=0.0, ask_px=state.best_ask, ask_sz=0.0)
