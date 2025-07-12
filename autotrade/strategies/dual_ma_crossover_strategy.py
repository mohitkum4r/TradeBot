import pandas as pd
import ta
from .base_strategy import BaseStrategy
from ..config import Config  # For new thresholds


class DualMaCrossoverStrategy(BaseStrategy):
    """
    A classic trend-following strategy based on the crossover of two moving averages.
    - Buy Signal (Golden Cross): Short-term MA crosses above long-term MA.
    - Sell Signal (Death Cross): Short-term MA crosses below long-term MA.
    Source: Algorithmic Trading NSE Strategies_.docx [cite: 1373, 1375]
    """

    def __init__(self, short_window=Config.MA_SHORT_WINDOW, long_window=Config.MA_LONG_WINDOW):  # Shortened for more signals
        self.short_window = short_window
        self.long_window = long_window
        # NEW: Cooldown tracker (class-level for simplicity; in production, use DB)
        self.cooldowns = {}  # {stock: remaining cooldown steps}

    def generate_signal(
        self, data: pd.DataFrame, sentiment_score: float = 0.0, stock: str = None  # Added stock for cooldown
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

        # NEW: Compute RSI and ADX for filters
        data["rsi"] = ta.momentum.RSIIndicator(data["close"], window=14).rsi()
        data["adx"] = ta.trend.ADXIndicator(data["high"], data["low"], data["close"], window=14).adx()

        last = data.iloc[-1]
        prev = data.iloc[-2]

        # NEW: Check cooldown (skip if in cooldown after loss)
        if stock and stock in self.cooldowns and self.cooldowns[stock] > 0:
            self.cooldowns[stock] -= 1
            return "HOLD", "In cooldown after recent loss."

        # Golden Cross Buy Signal [cite: 1380] with optimizations
        if last["short_ma"] > last["long_ma"] and prev["short_ma"] <= prev["long_ma"]:
            # NEW: Filters for better wins (RSI not oversold, sentiment positive, ADX trending)
            if last["rsi"] > Config.RSI_BUY_THRESHOLD and sentiment_score > 0 and last["adx"] > 20:  # Added ADX for trend confirmation
                return (
                    "BUY",
                    f"Golden Cross: {self.short_window}-day MA crossed above {self.long_window}-day MA. RSI: {last['rsi']:.2f}, ADX: {last['adx']:.2f}.",
                )
            else:
                return "HOLD", "Golden Cross but failed filters (low RSI/sentiment/ADX)."

        # Death Cross Sell Signal [cite: 1382] with optimizations
        if last["short_ma"] < last["long_ma"] and prev["short_ma"] >= prev["long_ma"]:
            # NEW: Filters to avoid bad sells (RSI not overbought, confirm downtrend with ADX)
            if last["rsi"] < 60 and sentiment_score < 0 and last["adx"] > Config.ADX_SELL_CONFIRM:  # Avoid selling in weak trends
                # NEW: Set cooldown after sell (if loss, but since we don't know yet, set always)
                if stock:
                    self.cooldowns[stock] = Config.COOLDOWN_AFTER_LOSS
                return (
                    "SELL",
                    f"Death Cross: {self.short_window}-day MA crossed below {self.long_window}-day MA. RSI: {last['rsi']:.2f}, ADX: {last['adx']:.2f}.",
                )
            else:
                return "HOLD", "Death Cross but failed filters (high RSI/sentiment/low ADX)."

        return "HOLD", "No crossover signal."