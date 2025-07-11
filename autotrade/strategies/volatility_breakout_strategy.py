# autotrade/strategies/volatility_breakout_strategy.py
import pandas as pd
import ta
from .base_strategy import BaseStrategy
from ..config import Config


class VolatilityBreakoutStrategy(BaseStrategy):
    """
    Buys on breakout above recent high with volume confirmation; sells on breakdown.
    Optimized for high-volatility regimes.
    """

    def __init__(self, window=Config.VOL_BREAKOUT_WINDOW, volume_multiplier=1.5):
        self.window = window
        self.volume_multiplier = volume_multiplier

    def generate_signal(
        self, data: pd.DataFrame, sentiment_score: float = 0.0
    ) -> tuple[str, str]:
        if len(data) < self.window:
            return "HOLD", "Insufficient data for breakout calculation."

        recent_high = data["high"].rolling(self.window).max().iloc[-1]
        recent_low = data["low"].rolling(self.window).min().iloc[-1]
        avg_volume = data["volume"].rolling(self.window).mean().iloc[-1]

        last = data.iloc[-1]

        if (
            last["close"] > recent_high
            and last["volume"] > avg_volume * self.volume_multiplier
            and sentiment_score > 0
        ):
            return "BUY", f"Breakout above {recent_high:.2f} with high volume."

        if last["close"] < recent_low and sentiment_score < 0:
            return "SELL", f"Breakdown below {recent_low:.2f}."

        return "HOLD", "No breakout signal."
