# domain/strategies/base_strategy.py
from abc import ABC, abstractmethod
import pandas as pd
from typing import List, Tuple, Dict, Any

class BaseStrategy(ABC):
    """
    Abstract Base Class for all trading strategies.
    """
    @abstractmethod
    def generate_signal(
        self, data: pd.DataFrame | Dict[str, pd.DataFrame], **kwargs: Any
    ) -> List[Tuple[str, str, str, Dict[str, float]]]:
        """
        Analyzes market data and generates trading signals.
        Returns: list of (stock/pair, signal, reason, extras dict with 'stop_loss', 'take_profit', 'size').
        """
        pass
