# autotrade/services/data_handler.py
import pandas as pd
from datetime import datetime, timedelta
from growwapi import GrowwAPI
from growwapi.groww.exceptions import GrowwAPIException
from tenacity import retry, stop_after_attempt, wait_exponential
import time
from typing import Dict, Union
from ..config import Config


class DataHandler:
    def __init__(self, client: GrowwAPI | None = None):
        if client is None:
            raise ValueError("GrowwAPI client is required for all data fetching operations.")
        self.client = client
        self.cache: Dict[str, pd.DataFrame] = {}  # In-memory cache

    def _fetch_single(self, stock: str, days: int, interval_minutes: int) -> pd.DataFrame:
        print(f"Fetching historical data for {stock} via Groww API (days={days}, interval={interval_minutes})...")
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)

            response = self.client.get_historical_candle_data(
                trading_symbol=stock,
                exchange=self.client.EXCHANGE_NSE,
                segment=self.client.SEGMENT_CASH,
                start_time=start_time.strftime("%Y-%m-%d %H:%M:%S"),
                end_time=end_time.strftime("%Y-%m-%d %H:%M:%S"),
                interval_in_minutes=interval_minutes,
            )

            if not response or "candles" not in response or not response["candles"]:
                print(f"No historical data found for {stock}.")
                return pd.DataFrame()

            df = pd.DataFrame(
                response["candles"],
                columns=["timestamp", "open", "high", "low", "close", "volume"],
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
            df.set_index("timestamp", inplace=True)
            print(f"Successfully fetched {len(df)} data points for {stock}.")
            return df

        except GrowwAPIException as e:
            print(f"Error fetching historical data for {stock}: {e}")
            raise

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=4, max=60))  # Longer backoff for rate limits
    def get_historical_data(
        self, stock: Union[str, list[str]], days: int = 90, interval_minutes: int = 60
    ) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
        # Auto-adjust to the smallest valid interval that can handle the days
        possible_intervals = sorted(Config.INTERVAL_ADJUST_MAP.keys())
        adjusted_interval = interval_minutes
        for intvl in possible_intervals:
            if days <= Config.INTERVAL_ADJUST_MAP[intvl]:
                adjusted_interval = intvl
                break
        else:
            # If no match, use the largest (weekly)
            adjusted_interval = max(possible_intervals)
        if adjusted_interval != interval_minutes:
            print(f"Auto-adjusted interval from {interval_minutes} to {adjusted_interval} minutes for {days} days to match API limits.")

        if isinstance(stock, str):
            cache_key = f"{stock}_{days}_{adjusted_interval}"
            if cache_key in self.cache:
                return self.cache[cache_key]
            df = self._fetch_single(stock, days, adjusted_interval)
            self.cache[cache_key] = df
            return df
        else:
            # Sequential fetch with delay and progress logging
            results = {}
            total_stocks = len(stock)
            for idx, s in enumerate(stock, 1):
                print(f"Fetching {idx}/{total_stocks}: {s}")
                cache_key = f"{s}_{days}_{adjusted_interval}"
                if cache_key in self.cache:
                    results[s] = self.cache[cache_key]
                    continue
                try:
                    df = self._fetch_single(s, days, adjusted_interval)
                    self.cache[cache_key] = df
                    results[s] = df
                except Exception as e:
                    print(f"Skipping {s} due to persistent error: {e}")
                time.sleep(Config.FETCH_DELAY_SECONDS)  # Delay to respect rate limits
            return {s: df for s, df in results.items() if not df.empty}

    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=4, max=60))
    def get_ltp(self, stock: str) -> float | None:
        print(f"Fetching LTP for {stock}...")
        try:
            symbol = f"NSE_{stock}"
            response = self.client.get_ltp(
                segment=self.client.SEGMENT_CASH, exchange_trading_symbols=(symbol,)
            )

            ltp = response.get(symbol)
            if ltp:
                print(f"LTP for {stock}: {ltp}")
                return float(ltp)
            else:
                print(f"LTP not found for {stock} in API response.")
                return None

        except GrowwAPIException as e:
            print(f"Error fetching LTP for {stock}: {e}")
            raise