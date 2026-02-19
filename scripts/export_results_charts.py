#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import random
from pathlib import Path

import matplotlib.pyplot as plt


def _load_payload(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def chart_01_baseline(payload: dict, outdir: Path) -> None:
    pnl = payload["series"]["pnl"]
    inventory = payload["series"]["inventory"]
    mid = payload["series"]["mid"]
    spread = payload["series"]["spread"]
    x = list(range(len(pnl)))

    fig, ax = plt.subplots(2, 2, figsize=(13, 8), sharex=True)
    ax[0][0].plot(x, pnl, color="tab:blue")
    ax[0][0].set_title("PnL")
    ax[0][0].grid(alpha=0.2)

    ax[0][1].plot(x, inventory, color="tab:orange")
    ax[0][1].set_title("Inventory")
    ax[0][1].grid(alpha=0.2)

    ax[1][0].plot(x, mid, color="tab:green")
    ax[1][0].set_title("Mid")
    ax[1][0].set_xlabel("Step")
    ax[1][0].grid(alpha=0.2)

    ax[1][1].plot(x, spread, color="tab:red")
    ax[1][1].set_title("Spread")
    ax[1][1].set_xlabel("Step")
    ax[1][1].grid(alpha=0.2)

    fig.suptitle("01 Baseline MM Overview")
    plt.tight_layout()
    fig.savefig(outdir / "01_baseline_mm_overview.png", dpi=160)
    plt.close(fig)


def chart_02_execution(payload: dict, outdir: Path) -> None:
    fills = payload["fills"]
    mid = payload["series"]["mid"]

    maker_count = 0
    taker_count = 0
    maker_fee = 0.0
    taker_fee = 0.0
    slippage = []
    post_move = []
    horizon = 10

    for f in fills:
        fee = float(f["fee"])
        side = f["side"]
        step = int(f["step"])
        price = float(f["price"])

        if fee <= 0.0:
            maker_count += 1
            maker_fee += fee
        else:
            taker_count += 1
            taker_fee += fee

        if 0 <= step < len(mid):
            m = mid[step]
            s = (price - m) if side == "buy" else (m - price)
            slippage.append(s)

        t2 = step + horizon
        if 0 <= step < len(mid) and 0 <= t2 < len(mid):
            v = (mid[t2] - mid[step]) if side == "buy" else (mid[step] - mid[t2])
            post_move.append(v)

    fig, ax = plt.subplots(2, 2, figsize=(13, 8))

    ax[0][0].bar(["maker", "taker"], [maker_count, taker_count], color=["tab:blue", "tab:orange"])
    ax[0][0].set_title("Fill Count Mix")

    ax[0][1].bar(["maker_fee", "taker_fee", "net_fee"], [maker_fee, taker_fee, maker_fee + taker_fee], color=["tab:green", "tab:red", "tab:purple"])
    ax[0][1].set_title("Fee Components")

    ax[1][0].hist(slippage, bins=35, color="tab:cyan", edgecolor="black", alpha=0.75)
    ax[1][0].set_title("Slippage Proxy")

    ax[1][1].hist(post_move, bins=35, color="tab:olive", edgecolor="black", alpha=0.75)
    ax[1][1].axvline(0.0, color="black", linestyle=":")
    ax[1][1].set_title("Adverse Selection Proxy")

    for i in range(2):
        for j in range(2):
            ax[i][j].grid(alpha=0.2)

    fig.suptitle("02 Execution Quality Diagnostics")
    plt.tight_layout()
    fig.savefig(outdir / "02_execution_quality.png", dpi=160)
    plt.close(fig)


def chart_03_funding_basis(payload: dict, outdir: Path) -> None:
    spot = payload["series"]["mid"]
    n = len(spot)

    rng = random.Random(11)
    dt = 1.0 / (365.0 * 24.0 * 60.0)
    kappa = 12.0
    basis_vol = 0.25
    basis = []
    b = 0.08
    for _ in range(n):
        shock = rng.gauss(0.0, basis_vol * math.sqrt(dt))
        b += -kappa * b * dt + shock
        b = max(-0.30, min(0.30, b))
        basis.append(b)

    perp = [s * (1.0 + bb / 365.0 / 24.0) for s, bb in zip(spot, basis)]

    entry_threshold = 0.05
    exit_threshold = 0.01
    notional = 10_000.0
    fee_bps = 2.0

    position = 0
    qty = 0.0
    carry_pnl = 0.0
    basis_pnl = 0.0
    total_cost = 0.0
    equity = []

    for t in range(1, n):
        s0, s1 = spot[t - 1], spot[t]
        p0, p1 = perp[t - 1], perp[t]
        b0 = basis[t - 1]

        if position == 0 and b0 >= entry_threshold:
            qty = notional / max(s0, 1e-9)
            total_cost += qty * (s0 + p0) * (fee_bps / 10_000.0)
            position = 1
        elif position == 1 and b0 <= exit_threshold:
            total_cost += qty * (s0 + p0) * (fee_bps / 10_000.0)
            position = 0
            qty = 0.0

        if position == 1:
            carry_pnl += (notional * b0) * dt
            spread0 = p0 - s0
            spread1 = p1 - s1
            basis_pnl += -qty * (spread1 - spread0)

        equity.append(carry_pnl + basis_pnl - total_cost)

    x = list(range(len(equity)))
    fig, ax = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    ax[0].plot([100.0 * x for x in basis], color="tab:green")
    ax[0].axhline(0.0, color="black", linestyle=":")
    ax[0].set_title("Annualized Basis (%)")
    ax[0].grid(alpha=0.2)

    ax[1].plot(x, equity, color="tab:blue")
    ax[1].set_title("Carry Strategy Equity")
    ax[1].set_xlabel("Step")
    ax[1].grid(alpha=0.2)

    fig.suptitle("03 Funding/Basis Arbitrage")
    plt.tight_layout()
    fig.savefig(outdir / "03_funding_basis_arb.png", dpi=160)
    plt.close(fig)


def chart_04_latency_arb(payload: dict, outdir: Path) -> None:
    base_mid = payload["series"]["mid"]
    n = len(base_mid)

    rng = random.Random(21)
    venue_a = []
    venue_b = []
    basis = 0.0
    for m in base_mid:
        basis += -0.08 * basis + rng.gauss(0.0, 0.01)
        venue_a.append(m + rng.gauss(0.0, 0.03))
        venue_b.append(m + basis + rng.gauss(0.0, 0.03))

    def run_latency_arb(latency_steps: int, transfer_delay: int, threshold: float = 0.12) -> float:
        fee_bps = 2.0
        qty = 1.0
        pnl = 0.0
        cooldown_until = -1
        for t in range(n - latency_steps - 1):
            if t < cooldown_until:
                continue
            spread_now = venue_b[t] - venue_a[t]
            side = 1 if spread_now > threshold else (-1 if -spread_now > threshold else 0)
            if side == 0:
                continue
            te = t + latency_steps
            tx = te + 1
            if tx >= n:
                continue
            a_in, b_in = venue_a[te], venue_b[te]
            a_out, b_out = venue_a[tx], venue_b[tx]
            gross = ((a_out - a_in) - (b_out - b_in)) if side == 1 else ((b_out - b_in) - (a_out - a_in))
            fees = qty * (a_in + b_in) * (fee_bps / 10_000.0)
            pnl += qty * gross - fees
            cooldown_until = t + transfer_delay
        return pnl

    latencies = [0, 1, 2, 3, 5, 8]
    delays = [1, 3, 5, 10, 20, 40]
    heat = []
    for L in latencies:
        row = []
        for D in delays:
            row.append(run_latency_arb(L, D))
        heat.append(row)

    fig, ax = plt.subplots(figsize=(9, 5))
    im = ax.imshow(heat, aspect="auto", origin="lower")
    ax.set_xticks(range(len(delays)))
    ax.set_xticklabels(delays)
    ax.set_yticks(range(len(latencies)))
    ax.set_yticklabels(latencies)
    ax.set_xlabel("Transfer delay (steps)")
    ax.set_ylabel("Signal latency (steps)")
    ax.set_title("04 Latency-Arb PnL Sensitivity")
    for i in range(len(latencies)):
        for j in range(len(delays)):
            ax.text(j, i, f"{heat[i][j]:.1f}", ha="center", va="center", color="white", fontsize=8)
    plt.colorbar(im, ax=ax)
    plt.tight_layout()
    fig.savefig(outdir / "04_two_venue_latency_arb.png", dpi=160)
    plt.close(fig)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    input_path = root / "outputs" / "baseline_mm_result.json"
    outdir = root / "results"
    outdir.mkdir(parents=True, exist_ok=True)

    payload = _load_payload(input_path)
    chart_01_baseline(payload, outdir)
    chart_02_execution(payload, outdir)
    chart_03_funding_basis(payload, outdir)
    chart_04_latency_arb(payload, outdir)

    print("Exported result charts to", outdir)


if __name__ == "__main__":
    main()
