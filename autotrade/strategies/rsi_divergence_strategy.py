import pandas as pd
import ta
from .base_strategy import BaseStrategy
from ..config import Config

class RsiDivergenceStrategy(BaseStrategy):
    """
    Identifies trading signals based on divergence between price and the RSI indicator.
    - Bullish Divergence: Price makes a new low, but RSI makes a higher low.
    - Bearish Divergence: Price makes a new high, but RSI makes a lower high.
    This can be a leading indicator for a potential trend reversal.
    """

    def __init__(self, rsi_period=None, lookback=None):
        self.rsi_period = rsi_period or Config.RSI_DIVERGENCE_PERIOD
        self.lookback = lookback or Config.RSI_DIVERGENCE_LOOKBACK


    def generate_signal(
        self, data: pd.DataFrame, sentiment_score: float = 0.0
    ) -> tuple[str, str]:
        if len(data) < self.rsi_period + self.lookback:
            return "HOLD", "Insufficient data for RSI Divergence analysis."

        # Calculate RSI
        data['rsi'] = ta.momentum.RSIIndicator(data['close'], window=self.rsi_period).rsi()

        data_slice = data.iloc[-self.lookback:]

        # Find the low/high points in the lookback period
        price_low = data_slice['low'].min()
        price_high = data_slice['high'].max()

        rsi_at_price_low = data_slice.loc[data_slice['low'] == price_low, 'rsi'].iloc[0]
        rsi_at_price_high = data_slice.loc[data_slice['high'] == price_high, 'rsi'].iloc[0]

        last_price = data.iloc[-1]['close']
        last_rsi = data.iloc[-1]['rsi']


        # --- Bullish Divergence Logic ---
        # Current price is at or near the period low, but current RSI is higher than RSI at the low.
        if (last_price <= price_low * 1.01) and (last_rsi > rsi_at_price_low):
            return "BUY", f"Bullish RSI divergence detected. Price low: {price_low:.2f}, RSI low: {rsi_at_price_low:.2f}, Current RSI: {last_rsi:.2f}"

        # --- Bearish Divergence Logic ---
        # Current price is at or near the period high, but current RSI is lower than RSI at the high.
        if (last_price >= price_high * 0.99) and (last_rsi < rsi_at_price_high):
            return "SELL", f"Bearish RSI divergence detected. Price high: {price_high:.2f}, RSI high: {rsi_at_price_high:.2f}, Current RSI: {last_rsi:.2f}"


        return "HOLD", "No clear RSI divergence detected."