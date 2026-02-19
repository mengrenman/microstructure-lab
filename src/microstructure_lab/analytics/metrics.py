from __future__ import annotations

import math
from statistics import mean, pstdev


def summarize(path: list[float], inventory: list[float], fills: int, fees_paid: float) -> dict[str, float]:
    pnl = [float(x) for x in path]
    rets = [pnl[i] - pnl[i - 1] for i in range(1, len(pnl))]

    mean_ret = float(mean(rets)) if rets else 0.0
    std_ret = float(pstdev(rets)) if len(rets) > 1 else 0.0
    sharpe = (mean_ret / std_ret * math.sqrt(252 * 24 * 60)) if std_ret > 0 else 0.0

    peak = float("-inf")
    max_dd = 0.0
    for x in pnl:
        peak = max(peak, x)
        max_dd = min(max_dd, x - peak)

    avg_abs_inv = float(mean(abs(x) for x in inventory)) if inventory else 0.0

    return {
        "final_pnl": float(pnl[-1]) if pnl else 0.0,
        "max_drawdown": max_dd,
        "sharpe_annualized": float(sharpe),
        "fills": float(fills),
        "fees_paid": float(fees_paid),
        "avg_abs_inventory": avg_abs_inv,
    }
