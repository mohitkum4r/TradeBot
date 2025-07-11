# autotrade/strategies/rsi_divergence_strategy.py
import pandas as pd
import ta
from .base_strategy import BaseStrategy
from ..config import Config


class RSIDivergenceStrategy(BaseStrategy):
    """
    Detects bullish (price lower low, RSI higher low) or bearish divergence.
    """

    def __init__(
        self, rsi_period=Config.RSI_PERIOD, window=Config.RSI_DIVERGENCE_WINDOW
    ):
        self.rsi_period = rsi_period
        self.window = window

    def generate_signal(
        self, data: pd.DataFrame, sentiment_score: float = 0.0
    ) -> tuple[str, str]:
        if len(data) < self.window + self.rsi_period:
            return "HOLD", "Insufficient data for RSI divergence."

        data["rsi"] = ta.momentum.RSIIndicator(
            data["close"], window=self.rsi_period
        ).rsi()

        # Simple divergence detection (last two lows/highs)
        price_lows = data["low"].rolling(self.window).min()
        rsi_lows = data["rsi"].rolling(self.window).min()
        price_highs = data["high"].rolling(self.window).max()
        rsi_highs = data["rsi"].rolling(self.window).max()

        # Bullish divergence
        if (
            price_lows.iloc[-1] < price_lows.iloc[-2]
            and rsi_lows.iloc[-1] > rsi_lows.iloc[-2]
        ):
            return "BUY", "Bullish RSI divergence detected."

        # Bearish divergence
        if (
            price_highs.iloc[-1] > price_highs.iloc[-2]
            and rsi_highs.iloc[-1] < rsi_highs.iloc[-2]
        ):
            return "SELL", "Bearish RSI divergence detected."

        return "HOLD", "No RSI divergence."
