from __future__ import annotations

from dataclasses import dataclass
from typing import Generator
import random

from microstructure_lab.types import MarketEvent


@dataclass
class SyntheticScenario:
    """Synthetic market scenario generator.

    Price process
    -------------
    Geometric Brownian Motion with configurable drift and a two-state
    Markov-switching volatility regime ("calm" / "stressed").  At each step
    the regime can transition according to ``calm_to_stressed_prob`` and
    ``stressed_to_calm_prob``.

    Spread
    ------
    The quoted spread widens with the absolute price shock so that high-vol
    periods naturally exhibit wider spreads::

        spread_ticks = max(base, base + spread_vol_sensitivity * |shock_bps|)

    Depth (multi-level)
    -------------------
    When ``depth_levels`` > 1 the scenario emits full ``bid_levels`` /
    ``ask_levels`` lists (consumed by the engine's ``set_depth`` path).
    Each level further from the touch gets geometrically larger size and is
    spaced by one additional tick.
    """

    seed: int
    start_mid: float
    tick_size: float
    steps: int

    # --- Volatility / regime ---
    sigma_bps: float                        # calm-regime per-step vol (bps)
    stressed_sigma_bps: float = 0.0        # stressed-regime vol; 0 = 2x calm
    calm_to_stressed_prob: float = 0.02
    stressed_to_calm_prob: float = 0.10

    # --- Drift ---
    drift_bps: float = 0.0                 # per-step drift (bps, GBM mu)

    # --- Spread ---
    spread_ticks: int = 2                  # base spread in ticks
    spread_vol_sensitivity: float = 2.0    # extra ticks per |sigma| unit

    # --- Depth ---
    depth_min: float = 1.0
    depth_max: float = 8.0
    depth_levels: int = 1                  # 1 = top-of-book only; >1 = multi-level

    def stream(self) -> Generator[MarketEvent, None, None]:
        rng = random.Random(self.seed)
        mid = self.start_mid
        stressed_sigma = self.stressed_sigma_bps if self.stressed_sigma_bps > 0 else self.sigma_bps * 2.0
        regime = "calm"

        for step in range(self.steps):
            # --- Regime transition (Markov chain) ---
            if regime == "calm":
                if rng.random() < self.calm_to_stressed_prob:
                    regime = "stressed"
            else:
                if rng.random() < self.stressed_to_calm_prob:
                    regime = "calm"

            current_sigma = self.sigma_bps if regime == "calm" else stressed_sigma

            # --- GBM price update with drift ---
            drift = self.drift_bps / 10_000.0
            shock = rng.gauss(0.0, current_sigma / 10_000.0)
            mid = max(self.tick_size, mid * (1.0 + drift + shock))

            # --- Vol-dependent spread ---
            shock_magnitude = abs(shock) * 10_000.0  # bps
            dynamic_spread_ticks = max(
                self.spread_ticks,
                self.spread_ticks + self.spread_vol_sensitivity * shock_magnitude,
            )
            half_spread = (dynamic_spread_ticks / 2.0) * self.tick_size
            best_bid = mid - half_spread
            best_ask = mid + half_spread

            # --- Depth generation ---
            if self.depth_levels <= 1:
                bid_size = rng.uniform(self.depth_min, self.depth_max)
                ask_size = rng.uniform(self.depth_min, self.depth_max)
                event: dict = {
                    "step": step,
                    "mid": mid,
                    "best_bid": best_bid,
                    "best_ask": best_ask,
                    "bid_size": bid_size,
                    "ask_size": ask_size,
                    "volatility": current_sigma / 10_000.0 * mid,
                    "regime": regime,
                }
            else:
                bid_levels, ask_levels = self._build_depth(rng, best_bid, best_ask, self.depth_levels)
                event = {
                    "step": step,
                    "mid": mid,
                    "best_bid": best_bid,
                    "best_ask": best_ask,
                    "bid_levels": bid_levels,
                    "ask_levels": ask_levels,
                    "volatility": current_sigma / 10_000.0 * mid,
                    "regime": regime,
                }

            yield event

    def _build_depth(
        self,
        rng: random.Random,
        best_bid: float,
        best_ask: float,
        n: int,
    ) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
        """Generate *n* levels each side with geometrically increasing size."""
        bid_levels: list[tuple[float, float]] = []
        ask_levels: list[tuple[float, float]] = []
        size_growth = 1.5  # each level ~50% larger than the previous
        for i in range(n):
            base_size = rng.uniform(self.depth_min, self.depth_max)
            level_size = base_size * (size_growth ** i)
            bid_price = best_bid - i * self.tick_size
            ask_price = best_ask + i * self.tick_size
            bid_levels.append((bid_price, level_size))
            ask_levels.append((ask_price, level_size))
        return bid_levels, ask_levels
