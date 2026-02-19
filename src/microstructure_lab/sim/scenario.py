from __future__ import annotations

from dataclasses import dataclass
import random


@dataclass
class SyntheticScenario:
    seed: int
    start_mid: float
    tick_size: float
    steps: int
    sigma_bps: float
    spread_ticks: int
    depth_min: float
    depth_max: float

    def stream(self):
        rng = random.Random(self.seed)
        mid = self.start_mid
        for step in range(self.steps):
            shock = rng.gauss(0.0, self.sigma_bps / 10_000.0)
            mid = max(self.tick_size, mid * (1.0 + shock))
            spread = max(1, self.spread_ticks) * self.tick_size

            best_bid = mid - spread / 2
            best_ask = mid + spread / 2
            bid_size = rng.uniform(self.depth_min, self.depth_max)
            ask_size = rng.uniform(self.depth_min, self.depth_max)

            yield {
                "step": step,
                "mid": mid,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "bid_size": bid_size,
                "ask_size": ask_size,
            }
