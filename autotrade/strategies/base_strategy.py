from abc import ABC, abstractmethod
import pandas as pd


class BaseStrategy(ABC):
    """
    Abstract Base Class for all trading strategies.
    """

    @abstractmethod
    def generate_signal(
        self, data: pd.DataFrame, sentiment_score: float = 0.0
    ) -> tuple[str, str]:
        """
        Analyzes market data and generates a trading signal.

        Args:
            data (pd.DataFrame): DataFrame with 'open', 'high', 'low', 'close', 'volume'.
                                 Index must be a datetime object.
            sentiment_score (float): A score from -1 (bearish) to 1 (bullish).

        Returns:
            tuple[str, str]: A tuple containing the signal ('BUY', 'SELL', 'HOLD')
                             and the reason for the signal.
        """
        pass
