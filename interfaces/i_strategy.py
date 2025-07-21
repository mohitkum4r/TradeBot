# interfaces/i_strategy.py
from abc import ABC, abstractmethod
import pandas as pd


class IStrategy(ABC):
    @abstractmethod
    def generate_signal(
        self, data: pd.DataFrame, **kwargs
    ) -> list[tuple[str, str, str]]:
        pass
