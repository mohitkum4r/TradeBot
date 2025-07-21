# domain/strategies/mean_reversion_strategy.py
import pandas as pd
import ta.volatility
import logging
from typing import List, Tuple, Dict, Any
from .base_strategy import BaseStrategy

logging.basicConfig(level=logging.INFO)

class MeanReversionStrategy(BaseStrategy):
    def __init__(
        self, bb_window: int = 20, bb_std_dev: int = 2, sentiment_threshold: float = 0.2
    ):
        self.bb_window = bb_window
        self.bb_std_dev = bb_std_dev
        self.sentiment_threshold = sentiment_threshold

    def generate_signal(
        self, data: Dict[str, pd.DataFrame], **kwargs: Any
    ) -> List[Tuple[str, str, str, Dict[str, float]]]:
        signals = []
        for stock, stock_data in data.items():
            sentiment_score = kwargs.get("sentiment_score", 0.0)  # Per-stock if available
            if len(stock_data) < self.bb_window:
                continue

            bb = ta.volatility.BollingerBands(stock_data["close"], window=self.bb_window, window_dev=self.bb_std_dev)
            stock_data["bb_high"] = bb.bollinger_hband().fillna(stock_data["close"].mean())
            stock_data["bb_low"] = bb.bollinger_lband().fillna(stock_data["close"].mean())

            last = stock_data.iloc[-1]
            if last["close"] < last["bb_low"] and sentiment_score >= -self.sentiment_threshold:
                extras = {"stop_loss": last["close"] * 0.95, "take_profit": last["bb_high"]}
                signals.append((stock, "BUY", f"Below lower BB {last['bb_low']:.2f}.", extras))
            elif last["close"] > last["bb_high"] and sentiment_score <= self.sentiment_threshold:
                extras = {"stop_loss": last["close"] * 1.05, "take_profit": last["bb_low"]}
                signals.append((stock, "SELL", f"Above upper BB {last['bb_high']:.2f}.", extras))
        return signals if signals else [("", "HOLD", "Price within Bollinger Bands.", {})]
