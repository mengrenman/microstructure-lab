"""Behavioral and statistical tests for strategies and the simulation engine.

These tests verify that the simulation behaves correctly at a semantic level —
not just that it runs, but that the outputs obey expected microstructure logic.
"""
from __future__ import annotations

import math

import pytest

from microstructure_lab.sim.engine import SimulationConfig, Simulator
from microstructure_lab.sim.scenario import SyntheticScenario
from microstructure_lab.strategies.market_maker import InventorySkewMM
from microstructure_lab.strategies.passive import DoNothingStrategy
from microstructure_lab.strategies.momentum import MomentumStrategy
from microstructure_lab.types import MarketState, QuoteIntent


def _scenario(steps: int = 300, seed: int = 1):
    return SyntheticScenario(
        seed=seed,
        start_mid=100.0,
        tick_size=0.5,
        steps=steps,
        sigma_bps=3.0,
        spread_ticks=2,
        depth_min=1.0,
        depth_max=5.0,
    )


def _sim(max_inv: float = 10.0, seed: int = 42) -> Simulator:
    return Simulator(SimulationConfig(max_inventory=max_inv, random_seed=seed))


# ------------------------------------------------------------------
# 1. DoNothing strategy: zero fills, zero PnL always
# ------------------------------------------------------------------

def test_do_nothing_has_no_fills():
    result = _sim().run(_scenario().stream(), DoNothingStrategy())
    assert len(result.fills) == 0


def test_do_nothing_pnl_is_zero():
    result = _sim().run(_scenario().stream(), DoNothingStrategy())
    assert all(p == 0.0 for p in result.pnl_path)


# ------------------------------------------------------------------
# 2. InventorySkewMM: symmetric quoting when penalty is zero
# ------------------------------------------------------------------

class SymmetricMM(InventorySkewMM):
    """MM with zero inventory penalty — should quote symmetrically around mid."""
    def __init__(self):
        super().__init__(half_spread_bps=3.0, inv_penalty_bps=0.0, quote_size=1.0)


def test_symmetric_mm_quotes_around_mid():
    """With inv_penalty=0, bid and ask should be equidistant from mid."""
    state = MarketState(
        step=0,
        mid=100.0,
        best_bid=99.5,
        best_ask=100.5,
        spread=1.0,
        imbalance=0.0,
        volatility=0.0,
    )
    mm = SymmetricMM()
    quote = mm.on_tick(state, inventory=0.0)
    half = state.mid * (3.0 / 10_000.0)
    assert math.isclose(quote.bid_px, state.mid - half, rel_tol=1e-9)
    assert math.isclose(quote.ask_px, state.mid + half, rel_tol=1e-9)


# ------------------------------------------------------------------
# 3. Higher inv_penalty_bps → lower avg_abs_inventory
# ------------------------------------------------------------------

def test_inv_penalty_skews_quotes_away_from_long_inventory():
    """When long, higher inventory penalty pulls the bid further below mid and
    the ask further below mid (skewing both toward selling) so that the
    strategy is more likely to get hit on its ask.

    This is a *quote* property test — fully deterministic, no stochastic fills.
    """
    state = MarketState(
        step=0,
        mid=100.0,
        best_bid=99.5,
        best_ask=100.5,
        spread=1.0,
        imbalance=0.0,
        volatility=0.0,
    )
    long_inventory = 5.0

    no_penalty = InventorySkewMM(half_spread_bps=3.0, inv_penalty_bps=0.0, quote_size=1.0)
    high_penalty = InventorySkewMM(half_spread_bps=3.0, inv_penalty_bps=2.0, quote_size=1.0)

    q_no = no_penalty.on_tick(state, long_inventory)
    q_hi = high_penalty.on_tick(state, long_inventory)

    # Penalty should push both quotes downward when long
    assert q_hi.bid_px < q_no.bid_px
    assert q_hi.ask_px < q_no.ask_px


def test_inv_penalty_is_zero_when_flat():
    """With zero inventory the penalty has no effect regardless of its magnitude."""
    state = MarketState(
        step=0, mid=100.0, best_bid=99.5, best_ask=100.5,
        spread=1.0, imbalance=0.0, volatility=0.0,
    )
    no_penalty = InventorySkewMM(half_spread_bps=3.0, inv_penalty_bps=0.0, quote_size=1.0)
    high_penalty = InventorySkewMM(half_spread_bps=3.0, inv_penalty_bps=10.0, quote_size=1.0)

    q_no = no_penalty.on_tick(state, 0.0)
    q_hi = high_penalty.on_tick(state, 0.0)

    assert math.isclose(q_no.bid_px, q_hi.bid_px)
    assert math.isclose(q_no.ask_px, q_hi.ask_px)


# ------------------------------------------------------------------
# 4. Adverse selection fields are populated after simulation
# ------------------------------------------------------------------

def test_adverse_selection_fields_populated():
    sim = Simulator(SimulationConfig(
        passive_fill_prob_base=0.5,  # high probability to ensure fills happen
        random_seed=7,
        adverse_selection_horizon=5,
    ))
    result = sim.run(_scenario(steps=200).stream(), InventorySkewMM())
    passive_fills = [f for f in result.fills if f.mid_before != 0.0]
    assert len(passive_fills) > 0, "Expected at least some passive fills"
    for f in passive_fills:
        assert f.mid_after != 0.0, "mid_after should be set for passive fills"
        assert math.isfinite(f.adverse_selection_cost)
        assert math.isfinite(f.realized_spread)


# ------------------------------------------------------------------
# 5. New summary metrics are present and finite
# ------------------------------------------------------------------

def test_summary_contains_new_metrics():
    result = _sim().run(_scenario().stream(), InventorySkewMM())
    required = {
        "inventory_half_life",
        "fill_rate",
        "realized_spread_avg",
        "adverse_selection_avg",
    }
    for key in required:
        assert key in result.summary, f"Missing metric: {key}"
        assert math.isfinite(result.summary[key]) or result.summary[key] == float("inf")


# ------------------------------------------------------------------
# 6. Scenario regime-switching: stressed_sigma produces wider spreads
# ------------------------------------------------------------------

def test_stressed_regime_produces_wider_average_spread():
    """Scenario with high stressed vol should produce wider average spread."""
    calm_only = SyntheticScenario(
        seed=42, start_mid=100.0, tick_size=0.5, steps=500,
        sigma_bps=2.0, stressed_sigma_bps=2.0,
        calm_to_stressed_prob=0.0,  # never transition
        stressed_to_calm_prob=1.0,
        spread_ticks=2, spread_vol_sensitivity=3.0,
        depth_min=1.0, depth_max=5.0,
    )
    stressed = SyntheticScenario(
        seed=42, start_mid=100.0, tick_size=0.5, steps=500,
        sigma_bps=2.0, stressed_sigma_bps=20.0,
        calm_to_stressed_prob=1.0,  # always stressed
        stressed_to_calm_prob=0.0,
        spread_ticks=2, spread_vol_sensitivity=3.0,
        depth_min=1.0, depth_max=5.0,
    )

    def avg_spread(scenario):
        events = list(scenario.stream())
        spreads = [e["best_ask"] - e["best_bid"] for e in events]
        return sum(spreads) / len(spreads)

    assert avg_spread(stressed) > avg_spread(calm_only)


# ------------------------------------------------------------------
# 7. Multi-level depth scenario populates more than one level per side
# ------------------------------------------------------------------

def test_multilevel_depth_scenario_emits_levels():
    scenario = SyntheticScenario(
        seed=1, start_mid=100.0, tick_size=0.5, steps=5,
        sigma_bps=2.0, spread_ticks=2, depth_min=1.0, depth_max=5.0,
        depth_levels=3,
    )
    events = list(scenario.stream())
    for event in events:
        assert "bid_levels" in event
        assert "ask_levels" in event
        assert len(event["bid_levels"]) == 3
        assert len(event["ask_levels"]) == 3


# ------------------------------------------------------------------
# 8. Strategy config: build_strategy dispatches correctly
# ------------------------------------------------------------------

def test_build_strategy_dispatches_by_type():
    from run_backtest import build_strategy

    mm = build_strategy({"type": "InventorySkewMM", "half_spread_bps": 5.0, "inv_penalty_bps": 1.0, "quote_size": 2.0})
    assert isinstance(mm, InventorySkewMM)
    assert mm.half_spread_bps == 5.0

    do_nothing = build_strategy({"type": "DoNothingStrategy"})
    assert isinstance(do_nothing, DoNothingStrategy)


def test_build_strategy_raises_on_unknown_type():
    from run_backtest import build_strategy
    with pytest.raises(ValueError, match="Unknown strategy type"):
        build_strategy({"type": "GarbageStrategy"})
