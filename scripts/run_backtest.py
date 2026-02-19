#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from microstructure_lab.sim.engine import SimulationConfig, Simulator
from microstructure_lab.sim.scenario import SyntheticScenario
from microstructure_lab.strategies.market_maker import InventorySkewMM


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run baseline microstructure backtest")
    parser.add_argument("--config", required=True, help="Path to JSON config")
    parser.add_argument("--output", default=None, help="Optional path to save full result JSON")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))

    scenario = SyntheticScenario(**cfg["scenario"])
    sim_cfg = SimulationConfig(**cfg["simulator"])
    strategy = InventorySkewMM(**cfg["strategy"])

    simulator = Simulator(sim_cfg)
    result = simulator.run(scenario.stream(), strategy)

    print("=== Simulation Summary ===")
    for k, v in result.summary.items():
        print(f"{k:>20s}: {v:,.6f}")

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
                }
                for f in result.fills
            ],
            "config": cfg,
        }
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"{'result_json':>20s}: {output_path}")


if __name__ == "__main__":
    main()
