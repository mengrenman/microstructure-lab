# microstructure-lab

A portfolio-oriented research repository for market microstructure, execution quality, and crypto-perp carry ideas.

## Project thesis

This repo demonstrates the workflow trading teams care about:

1. Form a hypothesis around microstructure or short-horizon inefficiency.
2. Test it in an event-driven simulation with realistic frictions.
3. Diagnose behavior using execution and risk analytics.
4. Iterate toward deployable research artifacts.

It is intentionally lightweight but engineered with production-like boundaries between simulator, strategy logic, and analytics.

## What is implemented

- Event-driven top-of-book simulation with stochastic passive/aggressive fills
- Inventory-aware market-making baseline strategy
- Fee-aware PnL accounting with inventory mark-to-mid
- Config-driven runs and deterministic random seeds
- Unit/smoke test coverage for core components
- Notebook-based analysis for strategy and execution diagnostics

## Repository structure

- `src/microstructure_lab/order_book.py`: top-of-book and imbalance model
- `src/microstructure_lab/sim/engine.py`: simulation engine and fill model
- `src/microstructure_lab/sim/scenario.py`: synthetic market state generator
- `src/microstructure_lab/strategies/market_maker.py`: inventory-skew MM strategy
- `src/microstructure_lab/analytics/metrics.py`: summary metrics and risk stats
- `scripts/run_backtest.py`: config runner and JSON export
- `configs/baseline_mm.json`: baseline experiment parameters
- `notebooks/01_baseline_mm_analysis.ipynb`: PnL, inventory, and market-state visuals
- `notebooks/02_execution_quality_analysis.ipynb`: maker/taker mix, fee drag, slippage and adverse-selection proxies
- `notebooks/03_funding_basis_arb_analysis.ipynb`: synthetic perp funding/basis carry study
- `notebooks/04_two_venue_latency_arb_analysis.ipynb`: cross-venue latency arbitrage stress tests
- `tests/`: unit and smoke tests

## Quickstart

```bash
cd /Users/mengren/Documents/New\ project/microstructure-lab
make run
make test
make report
```

`make report` writes `outputs/baseline_mm_result.json`, which powers the notebooks.

## Current baseline result snapshot

From `configs/baseline_mm.json` (latest local run):

- `final_pnl`: `2.009289`
- `max_drawdown`: `-5.844895`
- `sharpe_annualized`: `5.216777`
- `fills`: `372`
- `fees_paid`: `-1.153370`
- `avg_abs_inventory`: `2.289844`

These values are for synthetic data and are intended as diagnostics, not performance claims.

## Results gallery

Export figures with:

```bash
make results
```

Generated artifacts (one per notebook theme):

- `results/01_baseline_mm_overview.png`
- `results/02_execution_quality.png`
- `results/03_funding_basis_arb.png`
- `results/04_two_venue_latency_arb.png`

## Portfolio narrative

This repository is designed to signal fit for quant researcher / quant trader roles that require:

- market microstructure intuition
- realistic backtesting assumptions (fees, partial fills, inventory constraints)
- post-trade analysis and execution-quality diagnosis
- ability to move from hypothesis to testable, reproducible code

## Roadmap

1. L2/L3 historical order-book replay and queue-position modeling.
2. Perpetual futures module with exchange-specific funding mechanics and basis calibration.
3. Two-venue arbitrage simulator with latency, transfer delay, and inventory routing constraints.
4. Experiment tracking and report generation pipeline for strategy comparison.
5. CI workflow for tests plus notebook smoke checks.

## Notes

- `outputs/*.json` is ignored in git to keep the repo clean.
- Keep all model logic in `src/`; use notebooks for analysis only.
