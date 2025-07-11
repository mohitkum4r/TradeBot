from datetime import datetime, timedelta
from ..config import Config
from .data_handler import DataHandler
import pandas as pd
import ta
from statsmodels.tsa.stattools import coint
import time

# NEW: Function to dynamically update stocks and pairs using GrowwAPI
def update_dynamic_stocks(data_handler: DataHandler, days: int = 90):
    universe = Config.NSE_UNIVERSE  # Configurable list of NSE tickers
    data = {}
    for tick in universe:
        df = data_handler.get_historical_data(tick, days=days)
        if not df.empty:
            data[tick] = df
        time.sleep(Config.FETCH_DELAY_SECONDS)  # Respect GrowwAPI rate limits

    # Filter high-vol stocks using ATR
    high_vol_stocks = []
    for tick, df in data.items():
        if len(df) < 20: continue
        atr = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close']).average_true_range().iloc[-1]
        if atr > df['close'].iloc[-1] * 0.02:  # 2% threshold for high volatility
            high_vol_stocks.append(tick)

    # Dynamic pairs via cointegration test
    dynamic_pairs = []
    for i in range(len(high_vol_stocks)):
        for j in range(i + 1, len(high_vol_stocks)):
            s1 = data[high_vol_stocks[i]]['close']
            s2 = data[high_vol_stocks[j]]['close']
            if len(s1) == len(s2) and len(s1) > 60:
                _, pval, _ = coint(s1, s2)
                if pval < 0.05:
                    dynamic_pairs.append([high_vol_stocks[i], high_vol_stocks[j]])

    Config.STOCKS = high_vol_stocks[:20]  # Limit to top 20 for performance
    Config.PAIRS_LIST = dynamic_pairs[:10]  # Limit to top 10 pairs
    print(f"Updated via GrowwAPI: {len(Config.STOCKS)} stocks, {len(Config.PAIRS_LIST)} pairs")