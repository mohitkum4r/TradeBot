# domain/strategies/rsi_divergence_strategy.py
import pandas as pd
import ta.momentum
import logging
from typing import List, Tuple, Dict, Any
from .base_strategy import BaseStrategy
from app.config import Config

logging.basicConfig(level=logging.INFO)

class RSIDivergenceStrategy(BaseStrategy):
    def __init__(
        self,
        rsi_period: int = Config.RSI_PERIOD,
        window: int = Config.RSI_DIVERGENCE_WINDOW,
    ):
        self.rsi_period = rsi_period
        self.window = window

    def generate_signal(
        self, data: Dict[str, pd.DataFrame], **kwargs: Any
    ) -> List[Tuple[str, str, str, Dict[str, float]]]:
        signals = []
        for stock, stock_data in data.items():
            if len(stock_data) < self.window + self.rsi_period:
                continue

            stock_data["rsi"] = ta.momentum.RSIIndicator(stock_data["close"], window=self.rsi_period).rsi().fillna(50)
            price_lows = stock_data["low"].rolling(self.window).min().fillna(stock_data["low"].mean())
            rsi_lows = stock_data["rsi"].rolling(self.window).min().fillna(stock_data["rsi"].mean())
            price_highs = stock_data["high"].rolling(self.window).max().fillna(stock_data["high"].mean())
            rsi_highs = stock_data["rsi"].rolling(self.window).max().fillna(stock_data["rsi"].mean())

            last = stock_data.iloc[-1]
            if price_lows.iloc[-1] < price_lows.iloc[-2] and rsi_lows.iloc[-1] > rsi_lows.iloc[-2]:
                extras = {"stop_loss": last["low"] * 0.98, "take_profit": last["high"] * 1.05}
                signals.append((stock, "BUY", "Bullish RSI divergence.", extras))
            elif price_highs.iloc[-1] > price_highs.iloc[-2] and rsi_highs.iloc[-1] < rsi_highs.iloc[-2]:
                extras = {"stop_loss": last["high"] * 1.02, "take_profit": last["low"] * 0.95}
                signals.append((stock, "SELL", "Bearish RSI divergence.", extras))
        return signals if signals else [("", "HOLD", "No RSI divergence.", {})]
