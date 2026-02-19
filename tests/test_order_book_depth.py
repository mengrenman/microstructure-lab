"""Tests for multi-level order book functionality."""
from microstructure_lab.order_book import OrderBook


def test_depth_returns_correct_levels():
    book = OrderBook(tick_size=0.5)
    book.set_depth(
        bid_levels=[(99.5, 5.0), (99.0, 8.0), (98.5, 12.0)],
        ask_levels=[(100.5, 4.0), (101.0, 6.0), (101.5, 9.0)],
    )

    d = book.depth(2)
    assert len(d["bids"]) == 2
    assert len(d["asks"]) == 2
    # Bids should be descending (best first)
    assert d["bids"][0][0] == 99.5
    assert d["bids"][1][0] == 99.0
    # Asks should be ascending (best first)
    assert d["asks"][0][0] == 100.5
    assert d["asks"][1][0] == 101.0


def test_depth_clamps_to_available_levels():
    book = OrderBook(tick_size=0.5)
    book.set_top(best_bid=99.5, bid_size=3.0, best_ask=100.5, ask_size=2.0)
    d = book.depth(10)
    assert len(d["bids"]) == 1
    assert len(d["asks"]) == 1


def test_total_bid_ask_size():
    book = OrderBook(tick_size=0.5)
    book.set_depth(
        bid_levels=[(99.5, 5.0), (99.0, 3.0)],
        ask_levels=[(100.5, 4.0), (101.0, 6.0)],
    )
    assert book.total_bid_size(2) == 8.0
    assert book.total_ask_size(2) == 10.0


def test_depth_imbalance_sign():
    book = OrderBook(tick_size=0.5)
    book.set_depth(
        bid_levels=[(99.5, 10.0)],
        ask_levels=[(100.5, 2.0)],
    )
    # More bid depth → positive imbalance
    assert book.depth_imbalance(1) > 0


def test_weighted_mid_differs_from_arithmetic_mid():
    book = OrderBook(tick_size=0.5)
    # Heavy ask side → weighted mid closer to best ask
    book.set_top(best_bid=99.0, bid_size=1.0, best_ask=101.0, ask_size=9.0)
    assert book.weighted_mid() < book.mid()


def test_update_level_removes_at_zero():
    book = OrderBook(tick_size=0.5)
    book.set_top(best_bid=99.5, bid_size=5.0, best_ask=100.5, ask_size=5.0)
    book.update_level("bid", 99.5, 0.0)
    assert 99.5 not in book.bids
