import math

import pytest

from microstructure_lab.sim.engine import SimulationConfig, Simulator
from microstructure_lab.types import MarketState, QuoteIntent


class ConstantCrossBuyStrategy:
    def on_tick(self, state: MarketState, inventory: float) -> QuoteIntent:
        return QuoteIntent(
            bid_px=state.best_ask,
            bid_sz=5.0,
            ask_px=state.best_ask * 10.0,
            ask_sz=0.0,
        )


class InvalidStrategy:
    def on_tick(self, state: MarketState, inventory: float) -> QuoteIntent:
        return QuoteIntent(
            bid_px=state.best_bid,
            bid_sz=-1.0,
            ask_px=state.best_ask,
            ask_sz=1.0,
        )


def _fixed_events(n: int = 3):
    for step in range(n):
        yield {
            "step": step,
            "best_bid": 99.5,
            "best_ask": 100.5,
            "bid_size": 10.0,
            "ask_size": 10.0,
        }


def test_inventory_limit_enforced_pre_trade():
    sim = Simulator(
        SimulationConfig(
            aggressive_cross_prob=1.0,
            passive_fill_prob_base=0.0,
            taker_fee_bps=0.0,
            max_inventory=1.0,
        )
    )

    result = sim.run(_fixed_events(5), ConstantCrossBuyStrategy())

    assert max(result.inventory_path) <= 1.0
    assert result.inventory_path[-1] == 1.0


def test_invalid_quote_rejected():
    sim = Simulator(SimulationConfig())

    with pytest.raises(ValueError):
        sim.run(_fixed_events(1), InvalidStrategy())


def test_nan_quote_rejected():
    class NaNStrategy:
        def on_tick(self, state: MarketState, inventory: float) -> QuoteIntent:
            return QuoteIntent(
                bid_px=math.nan,
                bid_sz=1.0,
                ask_px=state.best_ask,
                ask_sz=1.0,
            )

    sim = Simulator(SimulationConfig())

    with pytest.raises(ValueError):
        sim.run(_fixed_events(1), NaNStrategy())
