import pandas as pd
import ta
from .base_strategy import BaseStrategy


class MomentumStrategy(BaseStrategy):
    """
    A strategy based on momentum indicators like RSI and MACD.
    Sentiment is used as a confirmation signal.
    """

    def __init__(
        self,
        rsi_period=14,
        macd_fast=12,
        macd_slow=26,
        macd_signal=9,
        sentiment_threshold=0.1,
    ):
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.sentiment_threshold = sentiment_threshold

    def generate_signal(
        self, data: pd.DataFrame, sentiment_score: float = 0.0
    ) -> tuple[str, str]:
        if len(data) < self.macd_slow:
            return "HOLD", "Insufficient historical data for MACD."

        # Calculate indicators
        data["rsi"] = ta.momentum.RSIIndicator(
            data["close"], window=self.rsi_period
        ).rsi()
        macd = ta.trend.MACD(
            data["close"],
            window_slow=self.macd_slow,
            window_fast=self.macd_fast,
            window_sign=self.macd_signal,
        )
        data["macd"] = macd.macd()
        data["macd_signal"] = macd.macd_signal()

        last = data.iloc[-1]
        prev = data.iloc[-2]

        # --- Buy Logic ---
        # Golden Cross: MACD crosses above its signal line
        is_macd_buy = (
            last["macd"] > last["macd_signal"] and prev["macd"] <= prev["macd_signal"]
        )
        is_rsi_ok_for_buy = last["rsi"] < 70  # Avoid buying when overbought

        # Sentiment confirmation
        sentiment_confirmation_buy = sentiment_score >= self.sentiment_threshold

        if is_macd_buy and is_rsi_ok_for_buy and sentiment_confirmation_buy:
            return (
                "BUY",
                f"MACD golden cross with RSI at {last['rsi']:.2f} and positive sentiment.",
            )

        # --- Sell Logic ---
        # Death Cross: MACD crosses below its signal line
        is_macd_sell = (
            last["macd"] < last["macd_signal"] and prev["macd"] >= prev["macd_signal"]
        )
        is_rsi_ok_for_sell = last["rsi"] > 30  # Avoid selling when oversold

        # Sentiment confirmation for sell
        sentiment_confirmation_sell = sentiment_score <= -self.sentiment_threshold

        if is_macd_sell and is_rsi_ok_for_sell and sentiment_confirmation_sell:
            return (
                "SELL",
                f"MACD death cross with RSI at {last['rsi']:.2f} and negative sentiment.",
            )

        return "HOLD", "No clear momentum signal."
