# use_cases/backtest_data.py
import pandas as pd
import ta  # Base import
import ta.trend  # Explicit for trend submodule
import ta.volatility  # Explicit for volatility submodule
import ta.momentum  # Explicit for momentum submodule
import logging
from utilities.date_utils import parse_backtest_dates
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Tuple, Dict
from app.config import Config
from infrastructure.data_providers.data_handler import DataHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

INTERVAL_ADJUST_MAP = {
    1: 7,     # 1 min: 7 days
    5: 15,    # 5 min: 15 days
    10: 30,   # 10 min: 30 days
    60: 150,  # 1 hour: 150 days
    240: 365, # 4 hours: 365 days
    1440: 1080, # 1 day: 1080 days (~3 years)
    10080: float("inf"),  # 1 week: no limit
}

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def fetch_data_with_retry(handler: DataHandler, symbol: str, start_time: str, end_time: str, interval: int) -> pd.DataFrame:
    data = handler.get_historical_data(symbol, interval, start_time, end_time)
    if data.empty:
        raise ValueError(f"No data for {symbol} from {start_time} to {end_time}")
    return data

def determine_optimal_interval(period_days: int) -> int:
    for interval, max_days in sorted(INTERVAL_ADJUST_MAP.items(), key=lambda x: x[0]):
        if period_days <= max_days:
            return interval
    logging.warning(f"Period {period_days} days exceeds limits; using 1-week interval.")
    return 10080  # Fallback to coarsest

def fetch_backtest_data(data_handler: DataHandler) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame, list[str], int]:
    start_dt, end_dt, period_days = parse_backtest_dates(Config)  # Use utility

    interval = determine_optimal_interval(period_days)
    logging.info(f"Backtesting from {start_dt} to {end_dt} ({period_days} days) with {interval}-min interval.")

    try:
        historical_data = {}
        for s in Config.STOCKS:
            try:
                historical_data[s] = fetch_data_with_retry(data_handler, s, start_dt, end_dt, interval)
            except Exception as e:
                logging.warning(f"Failed to fetch data for {s}: {e}. Skipping.")
        nifty_data = fetch_data_with_retry(data_handler, Config.MARKET_INDEX, start_dt, end_dt, interval)
    except Exception as e:
        logging.error(f"Critical data fetch failed: {e}")
        return {}, pd.DataFrame(), pd.DataFrame(), [], 0

    historical_data = {k: v for k, v in historical_data.items() if not v.empty}
    if not historical_data or nifty_data.empty:
        logging.warning("Insufficient data for backtest")
        return {}, pd.DataFrame(), pd.DataFrame(), [], 0

    combined_df = pd.concat({s: df for s, df in historical_data.items()}, axis=1, keys=historical_data.keys())
    stock_universe = list(historical_data.keys())
    min_length = min(len(combined_df.xs(s, level=0, axis=1)) for s in stock_universe) if stock_universe else 0  # Adjusted for MultiIndex
    if min_length < 14:
        logging.warning(f"Insufficient data length: {min_length}")
        return {}, pd.DataFrame(), pd.DataFrame(), [], 0

    return historical_data, nifty_data, combined_df, stock_universe, min_length

def calculate_indicators(stock_data: pd.DataFrame) -> Dict[str, float]:
    if len(stock_data) < 14:
        return {"adx": 0.0, "atr": 0.0, "rsi": 50.0}
    try:
        adx = ta.trend.ADXIndicator(stock_data["high"], stock_data["low"], stock_data["close"], window=14).adx().iloc[-1]
        adx = adx if not pd.isna(adx) else 0.0
    except Exception:
        adx = 0.0
    try:
        atr = ta.volatility.AverageTrueRange(stock_data["high"], stock_data["low"], stock_data["close"], window=14).average_true_range().iloc[-1]
        atr = atr if not pd.isna(atr) else 0.0
    except Exception:
        atr = 0.0
    try:
        rsi = ta.momentum.RSIIndicator(stock_data["close"], window=14).rsi().iloc[-1]
        rsi = rsi if not pd.isna(rsi) else 50.0
    except Exception:
        rsi = 50.0
    return {"adx": adx, "atr": atr, "rsi": rsi}

def get_optimal_signal(stock_data: pd.DataFrame, i: int) -> str:
    if i >= len(stock_data) - 1:
        return "HOLD"
    current_close = stock_data["close"].iloc[i - 1] if i > 0 else stock_data["close"].iloc[0]
    next_close = stock_data["close"].iloc[i]
    price_change_pct = (next_close - current_close) / current_close if current_close != 0 else 0
    return "BUY" if price_change_pct > 0.01 else "SELL" if price_change_pct < -0.01 else "HOLD"
