#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from microstructure_lab.sim.engine import SimulationConfig, Simulator
from microstructure_lab.sim.scenario import SyntheticScenario
from microstructure_lab.strategies.market_maker import InventorySkewMM
from microstructure_lab.strategies.twap import TWAPStrategy
from microstructure_lab.strategies.momentum import MomentumStrategy
from microstructure_lab.strategies.passive import DoNothingStrategy

_STRATEGY_REGISTRY = {
    "InventorySkewMM": InventorySkewMM,
    "TWAPStrategy": TWAPStrategy,
    "MomentumStrategy": MomentumStrategy,
    "DoNothingStrategy": DoNothingStrategy,
}


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_strategy(strategy_cfg: dict):
    """Instantiate a strategy from its config dict.

    The optional ``"type"`` key selects the strategy class.  All remaining
    keys are forwarded as constructor keyword arguments.  Defaults to
    ``InventorySkewMM`` for backwards compatibility.
    """
    cfg = dict(strategy_cfg)
    strategy_type = cfg.pop("type", "InventorySkewMM")
    cls = _STRATEGY_REGISTRY.get(strategy_type)
    if cls is None:
        known = ", ".join(sorted(_STRATEGY_REGISTRY))
        raise ValueError(f"Unknown strategy type {strategy_type!r}. Known: {known}")
    return cls(**cfg)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run microstructure backtest")
    parser.add_argument("--config", required=True, help="Path to JSON config")
    parser.add_argument("--output", default=None, help="Optional path to save full result JSON")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))

    scenario = SyntheticScenario(**cfg["scenario"])
    sim_cfg = SimulationConfig(**cfg["simulator"])
    strategy = build_strategy(cfg["strategy"])

    simulator = Simulator(sim_cfg)
    result = simulator.run(scenario.stream(), strategy)

    print("=== Simulation Summary ===")
    for k, v in result.summary.items():
        print(f"{k:>28s}: {v:,.6f}")

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "summary": result.summary,
            "series": {
                "pnl": result.pnl_path,
                "inventory": result.inventory_path,
                "mid": result.mid_path,
                "spread": result.spread_path,
            },
            "fills": [
                {
                    "step": f.step,
                    "side": f.side,
                    "price": f.price,
                    "size": f.size,
                    "fee": f.fee,
                    "mid_before": f.mid_before,
                    "mid_after": f.mid_after,
                    "adverse_selection_cost": f.adverse_selection_cost,
                    "realized_spread": f.realized_spread,
                }
                for f in result.fills
            ],
            "config": cfg,
        }
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"{'result_json':>28s}: {output_path}")


if __name__ == "__main__":
    main()
