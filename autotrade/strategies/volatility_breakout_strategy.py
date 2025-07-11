import pandas as pd
import ta
from .base_strategy import BaseStrategy
from ..config import Config

class VolatilityBreakoutStrategy(BaseStrategy):
    """
    A strategy that enters the market when volatility increases,
    as indicated by a price breakout from a Donchian Channel.
    It's designed to capture the beginning of strong moves.
    """

    def __init__(self, window=None, multiplier=None):
        self.window = window or Config.VOLATILITY_BREAKOUT_WINDOW
        self.multiplier = multiplier or Config.VOLATILITY_BREAKOUT_MULTIPLIER


    def generate_signal(
        self, data: pd.DataFrame, sentiment_score: float = 0.0
    ) -> tuple[str, str]:
        if len(data) < self.window:
            return "HOLD", "Insufficient historical data for Donchian Channel."

        # Calculate Donchian Channels
        data['upper_band'] = data['high'].rolling(self.window).max().shift(1)
        data['lower_band'] = data['low'].rolling(self.window).min().shift(1)

        last = data.iloc[-1]

        # --- Buy Logic ---
        # Price breaks above the upper Donchian Channel
        if last["close"] > last["upper_band"]:
            return (
                "BUY",
                f"Price broke above {self.window}-day high of {last['upper_band']:.2f}.",
            )

        # --- Sell Logic ---
        # Price breaks below the lower Donchian Channel
        if last["close"] < last["lower_band"]:
            return (
                "SELL",
                f"Price broke below {self.window}-day low of {last['lower_band']:.2f}.",
            )

        return "HOLD", "No volatility breakout."