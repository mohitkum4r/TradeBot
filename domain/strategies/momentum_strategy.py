# domain/strategies/momentum_strategy.py
import pandas as pd
import ta.momentum  # Explicit
import ta.trend  # Explicit
import logging
from .base_strategy import BaseStrategy

logging.basicConfig(level=logging.INFO)


class MomentumStrategy(BaseStrategy):
    def __init__(
        self,
        rsi_period: int = 14,
        macd_fast: int = 12,
        macd_slow: int = 26,
        macd_signal: int = 9,
        sentiment_threshold: float = 0.1,
    ):
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.sentiment_threshold = sentiment_threshold

    def generate_signal(
        self, data: pd.DataFrame, **kwargs
    ) -> list[tuple[str, str, str]]:
        sentiment_score = kwargs.get("sentiment_score", 0.0)
        stock = kwargs.get("stock", "")
        if len(data) < self.macd_slow:
            return [(stock, "HOLD", "Insufficient historical data for MACD.")]

        data["rsi"] = (
            ta.momentum.RSIIndicator(data["close"], window=self.rsi_period)
            .rsi()
            .fillna(50)
        )
        macd = ta.trend.MACD(
            data["close"],
            window_slow=self.macd_slow,
            window_fast=self.macd_fast,
            window_sign=self.macd_signal,
        )
        data["macd"] = macd.macd().fillna(0)
        data["macd_signal"] = macd.macd_signal().fillna(0)

        last = data.iloc[-1]
        prev = data.iloc[-2]

        is_macd_buy = (
            last["macd"] > last["macd_signal"] and prev["macd"] <= prev["macd_signal"]
        )
        is_rsi_ok_for_buy = last["rsi"] < 70
        sentiment_confirmation_buy = sentiment_score >= self.sentiment_threshold
        if is_macd_buy and is_rsi_ok_for_buy and sentiment_confirmation_buy:
            return [
                (
                    stock,
                    "BUY",
                    f"MACD golden cross with RSI at {last['rsi']:.2f} and positive sentiment.",
                )
            ]

        is_macd_sell = (
            last["macd"] < last["macd_signal"] and prev["macd"] >= prev["macd_signal"]
        )
        is_rsi_ok_for_sell = last["rsi"] > 30
        sentiment_confirmation_sell = sentiment_score <= -self.sentiment_threshold
        if is_macd_sell and is_rsi_ok_for_sell and sentiment_confirmation_sell:
            return [
                (
                    stock,
                    "SELL",
                    f"MACD death cross with RSI at {last['rsi']:.2f} and negative sentiment.",
                )
            ]

        return [(stock, "HOLD", "No clear momentum signal.")]
