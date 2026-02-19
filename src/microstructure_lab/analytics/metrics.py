from __future__ import annotations

import math
from statistics import mean, pstdev
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from microstructure_lab.types import Fill


def summarize(
    path: list[float],
    inventory: list[float],
    fills: "list[Fill] | int",
    fees_paid: float,
    periods_per_year: float,
) -> dict[str, float]:
    """Compute performance and microstructure metrics for a simulation run.

    Parameters
    ----------
    path:
        Mark-to-mid PnL at each step.
    inventory:
        Signed inventory at each step.
    fills:
        Either the raw ``list[Fill]`` objects (preferred) or a plain ``int``
        count (legacy, for tests that don't supply Fill objects).
    fees_paid:
        Total fees paid (positive = cost; negative = rebate received).
    periods_per_year:
        Number of simulation steps per calendar year, used to annualise Sharpe.
    """
    # ------------------------------------------------------------------
    # Standard performance metrics
    # ------------------------------------------------------------------
    pnl = [float(x) for x in path]
    rets = [pnl[i] - pnl[i - 1] for i in range(1, len(pnl))]

    mean_ret = float(mean(rets)) if rets else 0.0
    std_ret = float(pstdev(rets)) if len(rets) > 1 else 0.0
    annualization = math.sqrt(periods_per_year) if periods_per_year > 0 else 0.0
    sharpe = (mean_ret / std_ret * annualization) if std_ret > 0 else 0.0

    peak = float("-inf")
    max_dd = 0.0
    for x in pnl:
        peak = max(peak, x)
        max_dd = min(max_dd, x - peak)

    avg_abs_inv = float(mean(abs(x) for x in inventory)) if inventory else 0.0

    # ------------------------------------------------------------------
    # Inventory half-life
    # ------------------------------------------------------------------
    inv_half_life = _inventory_half_life(inventory)

    # ------------------------------------------------------------------
    # Microstructure metrics — require Fill objects
    # ------------------------------------------------------------------
    fill_count = 0
    realized_spread_avg = 0.0
    adverse_selection_avg = 0.0
    fill_rate = 0.0

    if isinstance(fills, list) and fills:
        fill_count = len(fills)
        passive_fills = [f for f in fills if f.mid_before != 0.0]

        if passive_fills:
            realized_spread_avg = float(mean(f.realized_spread for f in passive_fills))
            adverse_selection_avg = float(mean(f.adverse_selection_cost for f in passive_fills))

        n_steps = len(pnl)
        fill_rate = fill_count / n_steps if n_steps > 0 else 0.0
    elif isinstance(fills, int):
        fill_count = fills

    return {
        "final_pnl": float(pnl[-1]) if pnl else 0.0,
        "max_drawdown": max_dd,
        "sharpe_annualized": float(sharpe),
        "fills": float(fill_count),
        "fees_paid": float(fees_paid),
        "avg_abs_inventory": avg_abs_inv,
        "inventory_half_life": float(inv_half_life),
        "fill_rate": float(fill_rate),
        "realized_spread_avg": float(realized_spread_avg),
        "adverse_selection_avg": float(adverse_selection_avg),
    }


def _inventory_half_life(inventory: list[float]) -> float:
    """Estimate steps for |inventory| to decay to half its peak value."""
    if not inventory:
        return 0.0

    abs_inv = [abs(x) for x in inventory]
    peak_val = max(abs_inv)
    if peak_val < 1e-9:
        return 0.0

    peak_idx = abs_inv.index(peak_val)
    half_peak = peak_val / 2.0
    for i in range(peak_idx, len(abs_inv)):
        if abs_inv[i] <= half_peak:
            return float(i - peak_idx)
    return float("inf")


def microstructure_summary(result) -> dict[str, float]:
    """Compute additional microstructure diagnostics from a SimulationResult.

    Uses ``result.spread_path`` (not available inside ``summarize``) to
    compute the time-weighted average spread.
    """
    spread_path = result.spread_path
    tw_spread = float(mean(spread_path)) if spread_path else 0.0

    fills = result.fills
    quoted_half_spreads = [f.quoted_spread_half for f in fills if f.mid_before != 0.0]
    avg_quoted_half = float(mean(quoted_half_spreads)) if quoted_half_spreads else 0.0

    return {
        "time_weighted_avg_spread": tw_spread,
        "avg_quoted_half_spread": avg_quoted_half,
    }
