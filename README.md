# microstructure-lab

A portfolio-oriented research repository for market microstructure, execution quality, and
crypto-market carry/arbitrage ideas.

## Project thesis

This repo demonstrates the workflow trading teams care about:

1. Form a hypothesis around microstructure or short-horizon inefficiency.
2. Test it in an event-driven simulation with realistic frictions.
3. Diagnose behaviour using execution and risk analytics.
4. Iterate toward deployable research artifacts.

It is intentionally lightweight but engineered with production-like boundaries between
simulator, strategy logic, and analytics.

---

## What is implemented

### Simulation engine
- Event-driven limit-order-book simulation with **multi-level depth** (`set_depth`, `depth_imbalance`, `weighted_mid`)
- Stochastic passive fill model (exponential-decay probability) and aggressive cross model (vol-scaled probability)
- Fee-aware PnL accounting with inventory mark-to-mid
- Post-hoc **adverse selection annotation** on each fill (`mid_before`, `mid_after`, look-ahead horizon)
- Config-driven runs with deterministic random seeds

### Market scenario
- GBM price process with **Markov regime switching** (calm / stressed volatility)
- **Vol-dependent spread widening** (`spread_vol_sensitivity`)
- Configurable drift, multi-level depth generation

### Strategies
| Strategy | Type | Description |
|----------|------|-------------|
| `InventorySkewMM` | Passive maker | Quotes symmetrically around mid; skews quotes away from accumulated inventory side |
| `TWAPStrategy` | Passive taker | Slices a target inventory into equal child orders over `total_steps` |
| `MomentumStrategy` | Aggressive taker | Rolling-window return signal drives directional market orders |
| `DoNothingStrategy` | Control baseline | Never quotes; used to isolate pure market-state effects |

Strategy selection is config-driven via a `"type"` key — no code change needed to switch strategies.

### Analytics
Ten summary metrics per run:

| Metric | Description |
|--------|-------------|
| `final_pnl` | Mark-to-mid PnL at end of simulation |
| `max_drawdown` | Peak-to-trough PnL decline |
| `sharpe_annualized` | Annualised Sharpe ratio |
| `fills` | Total fill count |
| `fees_paid` | Net fees (negative = net rebate) |
| `avg_abs_inventory` | Average absolute inventory exposure |
| `inventory_half_life` | Steps for inventory to decay to half its peak |
| `fill_rate` | Fills per step |
| `realized_spread_avg` | Average realised half-spread per passive fill |
| `adverse_selection_avg` | Average adverse selection cost per passive fill |

### Notebooks
| Notebook | Topic |
|----------|-------|
| `01_baseline_mm_analysis` | PnL/inventory trajectory, vol-dependent spread, flow mix, microstructure decomposition |
| `02_execution_quality_analysis` | Maker/taker mix, fee drag, slippage proxy, spread decomposition histograms |
| `03_funding_basis_arb_analysis` | OU-process basis, delta-neutral carry strategy, P&L decomposition, threshold sweep |
| `04_two_venue_latency_arb_analysis` | Cross-venue basis, latency/transfer-delay stress grid, win-rate heatmap, threshold sensitivity |

All notebooks are papermill-compatible — override the `result_json` (and other) parameters from the CLI without editing source.

### Tests
24 tests across 6 files covering engine guards, order-book depth, metrics, simulation smoke, and
behavioural/statistical properties of every strategy.

---

## Repository structure

```
microstructure-lab/
├── src/microstructure_lab/
│   ├── types.py                     # MarketState, MarketEvent, QuoteIntent, Fill dataclasses
│   ├── order_book.py                # Multi-level order book: depth, imbalance, weighted mid
│   ├── sim/
│   │   ├── engine.py                # Simulation engine, fill model, adverse-selection annotation
│   │   └── scenario.py              # GBM + Markov regime switching scenario generator
│   ├── strategies/
│   │   ├── base.py                  # Abstract Strategy interface
│   │   ├── market_maker.py          # InventorySkewMM
│   │   ├── twap.py                  # TWAPStrategy
│   │   ├── momentum.py              # MomentumStrategy
│   │   └── passive.py               # DoNothingStrategy (control baseline)
│   └── analytics/
│       └── metrics.py               # summarize(), microstructure_summary()
├── scripts/
│   ├── run_backtest.py              # CLI runner: config → JSON output; strategy registry
│   └── export_results_charts.py     # Export portfolio PNGs to results/
├── configs/
│   ├── baseline_mm.json             # InventorySkewMM baseline
│   ├── twap.json                    # TWAPStrategy config
│   └── momentum.json                # MomentumStrategy config
├── notebooks/
│   ├── 01_baseline_mm_analysis.ipynb
│   ├── 02_execution_quality_analysis.ipynb
│   ├── 03_funding_basis_arb_analysis.ipynb
│   └── 04_two_venue_latency_arb_analysis.ipynb
├── tests/
│   ├── conftest.py
│   ├── test_engine_guards.py
│   ├── test_order_book.py
│   ├── test_order_book_depth.py
│   ├── test_metrics.py
│   ├── test_sim_smoke.py
│   └── test_behavioral.py
├── outputs/                         # Git-ignored; generated at runtime
├── results/                         # Exported PNG charts
├── Makefile
└── pyproject.toml
```

---

## Prerequisites

- **Python ≥ 3.9**
- **Conda** (default environment name: `microstructure`) — or any virtualenv with the packages below
- Runtime dependencies: `matplotlib` (notebooks only; no runtime deps for the core library)
- Dev dependency: `pytest ≥ 8.0`

Create and activate the environment:
```bash
conda create -n microstructure python=3.11
conda activate microstructure
pip install matplotlib
```

---

## Quickstart

```bash
# 1. Install the package in editable mode
make install

# 2. Run the baseline simulation (prints summary to stdout)
make run

# 3. Generate outputs/baseline_mm_result.json (required by notebooks)
make report

# 4. Run the full test suite
make test

# 5. Export portfolio PNGs to results/
make results
```

### Running other strategies

```bash
PYTHONPATH=src python scripts/run_backtest.py \
    --config configs/twap.json \
    --output outputs/twap_result.json

PYTHONPATH=src python scripts/run_backtest.py \
    --config configs/momentum.json \
    --output outputs/momentum_result.json
```

### Running notebooks with papermill

```bash
# Run NB01 against a custom result file
papermill notebooks/01_baseline_mm_analysis.ipynb outputs/nb01_out.ipynb \
    -p result_json outputs/twap_result.json
```

---

## Current baseline result snapshot

From `configs/baseline_mm.json` (2500 steps, `sigma_bps=4.0`, `inv_penalty_bps=0.8`):

| Metric | Value |
|--------|-------|
| `final_pnl` | `-3.387` |
| `max_drawdown` | `-21.073` |
| `sharpe_annualized` | `-2.485` |
| `fills` | `369` |
| `fees_paid` | `-1.139` (net rebate) |
| `avg_abs_inventory` | `6.078` |
| `inventory_half_life` | `inf` (inventory never reverted) |
| `fill_rate` | `0.148` |
| `realized_spread_avg` | `0.034` |
| `adverse_selection_avg` | `0.004` |

> Values are for **synthetic data only** — they are diagnostics, not performance claims.
> `inventory_half_life = inf` is expected for this parameter set; raise `inv_penalty_bps` to bring inventory under control.

---

## Results gallery

Export one PNG per notebook theme:

```bash
make results
```

Outputs written to `results/`:
- `01_baseline_mm_overview.png`
- `02_execution_quality.png`
- `03_funding_basis_arb.png`
- `04_two_venue_latency_arb.png`

---

## Portfolio narrative

This repository is designed to signal fit for quant researcher / quant trader roles that require:

- **Market microstructure intuition** — spread decomposition (Glosten-Milgrom), adverse selection measurement, inventory risk
- **Realistic backtesting assumptions** — fees, partial fills, inventory constraints, vol-dependent spreads
- **Post-trade analysis** — execution quality diagnosis at the fill level, slippage proxy, TCA framework
- **Research workflow discipline** — hypothesis → simulation → diagnostics → iteration, all reproducible and config-driven
- **Software engineering practices** — typed dataclasses, clean module boundaries, 24-test suite, papermill integration

---

## Roadmap

1. **L2/L3 order-book replay** — queue-position modelling, historical data ingestion pipeline.
2. **Funding mechanics** — real exchange-specific funding intervals, borrow costs, basis calibration from live data.
3. **Leg-risk modelling** — two-venue arb with stochastic fill on each leg independently.
4. **Experiment tracking** — strategy comparison dashboard, parameter-sweep pipeline with multi-run aggregation.
5. **CI workflow** — GitHub Actions: tests + notebook smoke checks on every push.

---

## Notes

- `outputs/*.json` is git-ignored; regenerate with `make report`.
- Keep all model logic in `src/`; notebooks are for analysis only.
- The `scripts/` directory is not a Python package — import from it in tests via the `conftest.py`-managed `sys.path`.
