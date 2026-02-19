from __future__ import annotations

from abc import ABC, abstractmethod

from microstructure_lab.types import MarketState, QuoteIntent


class Strategy(ABC):
    @abstractmethod
    def on_tick(self, state: MarketState, inventory: float) -> QuoteIntent:
        raise NotImplementedError
