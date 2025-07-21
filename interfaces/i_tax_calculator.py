from abc import ABC, abstractmethod
from domain.models.trade import Trade


class ITaxCalculator(ABC):
    @abstractmethod
    def calculate_taxes(self, trade: Trade) -> float:
        pass
