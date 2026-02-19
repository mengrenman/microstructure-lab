from microstructure_lab.order_book import OrderBook


def test_book_top_and_imbalance():
    book = OrderBook(tick_size=0.5)
    book.set_top(best_bid=99.5, bid_size=4.0, best_ask=100.5, ask_size=2.0)

    assert book.best_bid() == 99.5
    assert book.best_ask() == 100.5
    assert book.spread() == 1.0
    assert book.mid() == 100.0
    assert round(book.imbalance(), 6) == round((4.0 - 2.0) / 6.0, 6)
