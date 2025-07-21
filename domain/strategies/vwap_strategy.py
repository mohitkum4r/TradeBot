# domain/strategies/vwap_strategy.py
import pandas as pd
import ta.volume
import logging
from typing import List, Tuple, Dict, Any
from .base_strategy import BaseStrategy
from app.config import Config

logging.basicConfig(level=logging.INFO)

class VWAPStrategy(BaseStrategy):
    def __init__(self, window: int = Config.VWAP_WINDOW):
        self.window = window

    def generate_signal(
        self, data: Dict[str, pd.DataFrame], **kwargs: Any
    ) -> List[Tuple[str, str, str, Dict[str, float]]]:
        signals = []
        for stock, stock_data in data.items():
            sentiment_score = kwargs.get("sentiment_score", 0.0)
            if len(stock_data) < self.window:
                continue

            vwap_ind = ta.volume.VolumeWeightedAveragePrice(
                high=stock_data["high"], low=stock_data["low"], close=stock_data["close"], volume=stock_data["volume"], window=self.window
            )
            stock_data["vwap"] = vwap_ind.volume_weighted_average_price().fillna(stock_data["close"].mean())

            last = stock_data.iloc[-1]
            if last["close"] > last["vwap"] and sentiment_score > 0.2:
                extras = {"stop_loss": last["vwap"] * 0.98, "take_profit": last["close"] * 1.05}
                signals.append((stock, "BUY", f"Above VWAP {last['vwap']:.2f} with positive sentiment.", extras))
            elif last["close"] < last["vwap"] and sentiment_score < -0.2:
                extras = {"stop_loss": last["vwap"] * 1.02, "take_profit": last["close"] * 0.95}
                signals.append((stock, "SELL", f"Below VWAP {last['vwap']:.2f} with negative sentiment.", extras))
        return signals if signals else [("", "HOLD", "No VWAP crossover.", {})]
