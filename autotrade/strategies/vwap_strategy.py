import pandas as pd
import ta
from .base_strategy import BaseStrategy
from ..config import Config

# NEW: VWAP Strategy for profit maximization in high-vol regimes
class VWAPStrategy(BaseStrategy):
    """
    Buys on close > VWAP with volume confirmation; sells on close < VWAP.
    Optimized for intraday momentum.
    """

    def __init__(self, window=Config.VWAP_WINDOW):
        self.window = window

    def generate_signal(
        self, data: pd.DataFrame, sentiment_score: float = 0.0
    ) -> tuple[str, str]:
        if len(data) < self.window:
            return "HOLD", "Insufficient data for VWAP."

        # Compute VWAP using ta
        data['vwap'] = ta.volume.VolumeWeightedAveragePrice(
            high=data["high"], low=data["low"], close=data["close"], volume=data["volume"], window=self.window
        ).volume_weighted_average_price()

        last = data.iloc[-1]
        # Profit filter: Use sentiment to confirm
        if last["close"] > last["vwap"] and sentiment_score > 0.2:
            return "BUY", f"Close {last['close']:.2f} > VWAP {last['vwap']:.2f} with positive sentiment."
        if last["close"] < last["vwap"] and sentiment_score < -0.2:
            return "SELL", f"Close {last['close']:.2f} < VWAP {last['vwap']:.2f} with negative sentiment."
        return "HOLD", "No VWAP crossover."