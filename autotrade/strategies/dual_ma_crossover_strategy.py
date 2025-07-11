# autotrade/strategies/dual_ma_crossover_strategy.py

import pandas as pd
import ta
from .base_strategy import BaseStrategy


class DualMaCrossoverStrategy(BaseStrategy):
    """
    A classic trend-following strategy based on the crossover of two moving averages.
    - Buy Signal (Golden Cross): Short-term MA crosses above long-term MA.
    - Sell Signal (Death Cross): Short-term MA crosses below long-term MA.
    Source: Algorithmic Trading NSE Strategies_.docx [cite: 1373, 1375]
    """

    def __init__(self, short_window=20, long_window=50):  # Shortened for more signals
        self.short_window = short_window
        self.long_window = long_window

    def generate_signal(
        self, data: pd.DataFrame, sentiment_score: float = 0.0
    ) -> tuple[str, str]:
        min_length = max(self.short_window, self.long_window) + 1
        if len(data) < min_length:
            return "HOLD", f"Insufficient historical data (need {min_length} points)."

        # Make a copy to avoid SettingWithCopyWarning
        data = data.copy()

        # Calculate short and long term Exponential Moving Averages (EMAs) using .loc
        # EMAs give more weight to recent prices, making them more responsive. [cite: 1296]
        data.loc[:, "short_ma"] = ta.trend.ema_indicator(
            data["close"], window=self.short_window
        )
        data.loc[:, "long_ma"] = ta.trend.ema_indicator(data["close"], window=self.long_window)

        last = data.iloc[-1]
        prev = data.iloc[-2]

        # Golden Cross Buy Signal [cite: 1380]
        if last["short_ma"] > last["long_ma"] and prev["short_ma"] <= prev["long_ma"]:
            return (
                "BUY",
                f"Golden Cross: {self.short_window}-day MA crossed above {self.long_window}-day MA.",
            )

        # Death Cross Sell Signal [cite: 1382]
        if last["short_ma"] < last["long_ma"] and prev["short_ma"] >= prev["long_ma"]:
            return (
                "SELL",
                f"Death Cross: {self.short_window}-day MA crossed below {self.long_window}-day MA.",
            )

        return "HOLD", "No crossover signal."