# microstructure-lab

![CI](https://github.com/mengrenman/microstructure-lab/actions/workflows/ci.yml/badge.svg)

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
| [`01_baseline_mm_analysis`](notebooks/01_baseline_mm_analysis.ipynb) | PnL/inventory trajectory, vol-dependent spread, flow mix, microstructure decomposition |
| [`02_execution_quality_analysis`](notebooks/02_execution_quality_analysis.ipynb) | Maker/taker mix, fee drag, slippage proxy, spread decomposition histograms |
| [`03_funding_basis_arb_analysis`](notebooks/03_funding_basis_arb_analysis.ipynb) | OU-process basis, delta-neutral carry strategy, P&L decomposition, threshold sweep |
| [`04_two_venue_latency_arb_analysis`](notebooks/04_two_venue_latency_arb_analysis.ipynb) | Cross-venue basis, latency/transfer-delay stress grid, win-rate heatmap, threshold sensitivity |

All notebooks are papermill-compatible — override the `result_json` (and other) parameters from the CLI without editing source.

### Tests
24 tests across 6 files covering engine guards, order-book depth, metrics, simulation smoke, and
behavioural/statistical properties of every strategy.

---

## Simulation model

The simulation is fundamentally an **interacting system of stochastic processes**: two state processes drive the market, two Bernoulli processes govern how the strategy interacts with it, and one deterministic feedback loop connects fill outcomes back into the next step's quoting behaviour.

What makes it interesting is the coupling: `σ(t)` drives the mid shocks, the spread, and the aggressive cross probability simultaneously. A single regime switch ripples through every part of the system at once — price moves faster, spread widens, informed flow arrives more frequently, and fill probabilities all change in the same step. That joint behaviour is what naive backtests on mid-prices miss entirely.

The simulation models a market using two coupled stochastic processes. Everything else — spread, fill probability, aggressive flow — is derived from them.

### State variables

| Variable | Process | Role |
|----------|---------|------|
| `mid(t)` | Regime-switching GBM | Fair value of the asset |
| `σ(t)` | Two-state Markov chain | Volatility regime (calm / stressed) |

**Volatility regime** switches at each step:
```
P( calm → stressed ) = 0.02      expected stressed duration: 1/0.10 = 10 steps
P( stressed → calm ) = 0.10
```

**Mid price** is driven by `σ(t)`:
```
mid(t+1) = mid(t) · exp( μ + σ(t) · Z ),    Z ~ N(0,1)
```

In stressed regimes the mid moves more violently, the spread widens, and aggressive flow arrives more frequently — all because the same `σ(t)` feeds into every downstream quantity.

### Derived market quantities (deterministic given state)

- **Spread** — widens proportionally to `|return(t)|` via `spread_vol_sensitivity`
- **Bid / ask** — set by the strategy around mid, shifted by an inventory skew term (`inv_penalty_bps`)
- **Depth** — multi-level quantities (`depth_imbalance`, `weighted_mid`) derived from spread and a depth-generation function

### Interaction channels (stochastic given state)

The strategy interacts with the market through two Bernoulli processes, one per step:

**Passive fill** — models uninformed flow drifting into resting quotes:
```
P(fill) = exp( -α · d ),    d = distance from quote to mid
```
Closer quotes are more likely to fill. Queue position and individual order mechanics are collapsed into this single probability — the key simplification relative to a full LOB simulation.

**Aggressive cross** — models informed or urgent flow that crosses the spread immediately:
```
P(cross) ∝ σ(t)
```
This is doubly stochastic: the regime randomises `σ(t)`, which then randomises the cross probability. Aggressive crosses cluster in stressed periods.

### PnL accounting

```
PnL(t) = cash(t) + inventory(t) × mid(t)
```

Inventory is marked to mid at every step, so holding a position when the mid moves against you registers as an immediate loss — regardless of whether you have traded. Fees (maker rebate / taker fee) are deducted from cash on every fill.

The core tension the simulation measures: **spread capture** (earned on each fill) versus **inventory risk** (loss when mid moves against accumulated position). The `inv_penalty_bps` skew mechanism is the strategy's tool for managing that trade-off.

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
├── slides/
│   ├── microstructure_lab_presentation.tex  # Beamer slide deck source
│   └── microstructure_lab_presentation.pdf  # Compiled presentation (18 slides)
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

From `configs/baseline_mm.json` (2500 steps, `sigma_bps=4.0`, `inv_penalty_bps=7.5`):

| Metric | Value |
|--------|-------|
| `final_pnl` | `+1.725` |
| `max_drawdown` | `-9.472` |
| `sharpe_annualized` | `+2.314` |
| `fills` | `377` |
| `fees_paid` | `-1.165` (net rebate) |
| `avg_abs_inventory` | `2.650` |
| `inventory_half_life` | `118` steps |
| `fill_rate` | `0.151` |
| `realized_spread_avg` | `0.003` |
| `adverse_selection_avg` | `0.001` |

> Values are for **synthetic data only** — they are diagnostics, not performance claims.

**Tuning note:** `inv_penalty_bps=7.5` is the calibrated value that keeps `inventory_half_life` finite
(≈118 steps). Below ~6 bps the inventory never mean-reverts (`half_life=inf`); above ~8 bps the
penalty skew starts crossing the spread aggressively, compressing `realized_spread_avg`.
The 7.5 bps setting balances inventory control (avg|inv|≈2.65 vs. ≈6.1 untuned) with a positive Sharpe.
The NB01 penalty sweep reproduces the full `inv_penalty_bps` sensitivity grid.

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

Done:
- ✅ **CI workflow** — GitHub Actions: pytest across Python 3.10–3.12 + papermill notebook smoke checks on every push.

Upcoming:
1. **L2/L3 order-book replay** — queue-position modelling, historical data ingestion pipeline.
2. **Real price / funding data** — replace synthetic series with Binance perpetual funding-rate history via public REST API.
3. **Funding mechanics** — real exchange-specific funding intervals, borrow costs, basis calibration from live data.
4. **Leg-risk modelling** — two-venue arb with stochastic fill on each leg independently.
5. **Experiment tracking** — strategy comparison dashboard, parameter-sweep pipeline with multi-run aggregation.

---

## Slide deck

A self-contained Beamer presentation covering the full codebase is in `slides/`:

```bash
cd slides
pdflatex microstructure_lab_presentation.tex   # run twice for TOC/nav
```

The compiled PDF (`microstructure_lab_presentation.pdf`, 18 slides) is committed and can be shared directly.

---

## Notes

- `outputs/` is git-ignored; regenerate JSON outputs with `make report` and PNGs with `make results`.
- Keep all model logic in `src/`; notebooks are for analysis only.
- The `scripts/` directory is not a Python package — import from it in tests via the `conftest.py`-managed `sys.path`.
- LaTeX auxiliary files (`*.aux`, `*.log`, `*.nav`, `*.snm`, etc.) in `slides/` are git-ignored.
