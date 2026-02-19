from __future__ import annotations

from dataclasses import dataclass, field
import math
import random

from microstructure_lab.analytics.metrics import summarize
from microstructure_lab.order_book import OrderBook
from microstructure_lab.strategies.base import Strategy
from microstructure_lab.types import Fill, MarketState


@dataclass
class SimulationConfig:
    tick_size: float = 0.5
    maker_fee_bps: float = -0.5
    taker_fee_bps: float = 2.0
    # Base probability that the strategy quote crosses the touch and lifts immediately.
    # Scaled up by realized volatility at runtime.
    aggressive_cross_prob: float = 0.03
    passive_fill_prob_base: float = 0.08
    max_inventory: float = 10.0
    periods_per_year: float = 365.0 * 24.0 * 60.0
    random_seed: int = 42
    # How many steps ahead to measure adverse selection (0 = disabled).
    adverse_selection_horizon: int = 5


@dataclass
class SimulationResult:
    pnl_path: list[float] = field(default_factory=list)
    inventory_path: list[float] = field(default_factory=list)
    mid_path: list[float] = field(default_factory=list)
    spread_path: list[float] = field(default_factory=list)
    fills: list[Fill] = field(default_factory=list)
    summary: dict[str, float] = field(default_factory=dict)


class Simulator:
    def __init__(self, cfg: SimulationConfig):
        self.cfg = cfg
        self.rng = random.Random(cfg.random_seed)

    def run(self, scenario_stream, strategy: Strategy) -> SimulationResult:
        book = OrderBook(tick_size=self.cfg.tick_size)
        cash = 0.0
        inv = 0.0
        fees_paid = 0.0

        pnl_path: list[float] = []
        inv_path: list[float] = []
        mid_path: list[float] = []
        spread_path: list[float] = []
        fills: list[Fill] = []

        # Eagerly consume the stream so we can do look-ahead for adverse selection.
        events = list(scenario_stream)

        for idx, event in enumerate(events):
            # Build order book snapshot.  The scenario may supply multi-level depth
            # via "bid_levels" / "ask_levels"; fall back to single top-of-book.
            if "bid_levels" in event and "ask_levels" in event:
                book.set_depth(event["bid_levels"], event["ask_levels"])
            else:
                book.set_top(
                    best_bid=event["best_bid"],
                    bid_size=event["bid_size"],
                    best_ask=event["best_ask"],
                    ask_size=event["ask_size"],
                )

            state = MarketState(
                step=event["step"],
                mid=book.mid(),
                best_bid=book.best_bid(),
                best_ask=book.best_ask(),
                spread=book.spread(),
                imbalance=book.imbalance(),
                volatility=float(event.get("volatility", 0.0)),
                regime=str(event.get("regime", "calm")),
            )

            quote = strategy.on_tick(state, inv)
            self._validate_quote(quote)

            step_fills = self._simulate_fills(state, quote, inv)
            for fill in step_fills:
                size = self._bounded_fill_size(fill.side, fill.size, inv)
                if size <= 0.0:
                    continue

                fee = fill.fee * (size / fill.size) if fill.size > 0 else 0.0
                bounded_fill = Fill(
                    side=fill.side,
                    price=fill.price,
                    size=size,
                    fee=fee,
                    step=fill.step,
                    mid_before=state.mid,
                )

                if bounded_fill.side == "buy":
                    inv += bounded_fill.size
                    cash -= bounded_fill.price * bounded_fill.size
                else:
                    inv -= bounded_fill.size
                    cash += bounded_fill.price * bounded_fill.size
                cash -= bounded_fill.fee
                fees_paid += bounded_fill.fee
                fills.append(bounded_fill)

            mtm = cash + inv * state.mid
            pnl_path.append(mtm)
            inv_path.append(inv)
            mid_path.append(state.mid)
            spread_path.append(state.spread)

        # ------------------------------------------------------------------
        # Post-hoc adverse-selection annotation
        # For each fill, look forward ``adverse_selection_horizon`` steps and
        # record the mid price there.  Fills near the end of the series get the
        # final mid as a fallback.
        # ------------------------------------------------------------------
        horizon = self.cfg.adverse_selection_horizon
        if horizon > 0 and mid_path:
            for f in fills:
                future_idx = min(f.step + horizon, len(mid_path) - 1)
                f.mid_after = mid_path[future_idx]

        result = SimulationResult(
            pnl_path=pnl_path,
            inventory_path=inv_path,
            mid_path=mid_path,
            spread_path=spread_path,
            fills=fills,
        )
        result.summary = summarize(
            path=pnl_path,
            inventory=inv_path,
            fills=fills,
            fees_paid=fees_paid,
            periods_per_year=self.cfg.periods_per_year,
        )
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_quote(self, quote) -> None:
        fields = (
            ("bid_px", quote.bid_px),
            ("ask_px", quote.ask_px),
            ("bid_sz", quote.bid_sz),
            ("ask_sz", quote.ask_sz),
        )
        for name, value in fields:
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"Invalid quote value for {name}: {value!r}")

        if quote.bid_px < 0.0 or quote.ask_px < 0.0:
            raise ValueError("Quote prices must be non-negative")
        if quote.bid_sz < 0.0 or quote.ask_sz < 0.0:
            raise ValueError("Quote sizes must be non-negative")
        if quote.ask_px < quote.bid_px:
            raise ValueError("Quote ask price must be >= bid price")

    def _bounded_fill_size(self, side: str, size: float, inventory: float) -> float:
        if size <= 0.0:
            return 0.0

        if side == "buy":
            room = self.cfg.max_inventory - inventory
            return max(0.0, min(size, room))

        if side == "sell":
            room = inventory + self.cfg.max_inventory
            return max(0.0, min(size, room))

        raise ValueError(f"Unknown fill side: {side!r}")

    def _simulate_fills(self, state: MarketState, quote, inventory: float) -> list[Fill]:
        fills: list[Fill] = []

        # Aggressive cross probability scales with realized volatility so that
        # in stressed regimes (high vol) quotes are more likely to inadvertently
        # cross the touch.
        vol_scale = 1.0 + max(0.0, state.volatility / max(state.spread, 1e-9))
        cross_prob = min(1.0, self.cfg.aggressive_cross_prob * vol_scale)

        # Aggressive crosses: strategy quote crosses touch → immediate taker fill.
        if quote.bid_px >= state.best_ask and self.rng.random() < cross_prob:
            size = min(quote.bid_sz, 1.0)
            fee = state.best_ask * size * (self.cfg.taker_fee_bps / 10_000.0)
            fills.append(Fill(side="buy", price=state.best_ask, size=size, fee=fee, step=state.step))

        if quote.ask_px <= state.best_bid and self.rng.random() < cross_prob:
            size = min(quote.ask_sz, 1.0)
            fee = state.best_bid * size * (self.cfg.taker_fee_bps / 10_000.0)
            fills.append(Fill(side="sell", price=state.best_bid, size=size, fee=fee, step=state.step))

        # Passive fills: stochastic hit probability decays exponentially with
        # distance from touch and is biased by book imbalance.
        dist_bid_ticks = max(0.0, (state.best_bid - quote.bid_px) / max(self.cfg.tick_size, 1e-9))
        dist_ask_ticks = max(0.0, (quote.ask_px - state.best_ask) / max(self.cfg.tick_size, 1e-9))

        p_hit_bid = self.cfg.passive_fill_prob_base * (1.0 - 0.5 * state.imbalance) * math.exp(-dist_bid_ticks)
        p_hit_ask = self.cfg.passive_fill_prob_base * (1.0 + 0.5 * state.imbalance) * math.exp(-dist_ask_ticks)
        p_hit_bid = max(0.0, min(1.0, p_hit_bid))
        p_hit_ask = max(0.0, min(1.0, p_hit_ask))

        if quote.bid_px < state.best_ask and self.rng.random() < p_hit_bid:
            size = quote.bid_sz * self.rng.uniform(0.2, 1.0)
            fee = quote.bid_px * size * (self.cfg.maker_fee_bps / 10_000.0)
            fills.append(Fill(side="buy", price=quote.bid_px, size=size, fee=fee, step=state.step))

        if quote.ask_px > state.best_bid and self.rng.random() < p_hit_ask:
            size = quote.ask_sz * self.rng.uniform(0.2, 1.0)
            fee = quote.ask_px * size * (self.cfg.maker_fee_bps / 10_000.0)
            fills.append(Fill(side="sell", price=quote.ask_px, size=size, fee=fee, step=state.step))

        return fills
