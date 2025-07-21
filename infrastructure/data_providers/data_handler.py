# infrastructure/data_providers/data_handler.py
from datetime import datetime, timedelta
import pandas as pd
from interfaces.i_data_provider import IDataProvider
from app.config import Config
import time
import logging
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

class DataHandler:
    def __init__(self, data_provider: IDataProvider):
        self._data_provider = data_provider
        self._cache = {}
        self._cache_expiry = timedelta(minutes=5)

    @retry(
        stop=stop_after_attempt(5),  # Increased retries
        wait=wait_fixed(10),  # Increased wait to 10s to handle rate limits
        retry=retry_if_exception_type(Exception),  # Retry on any exception
        reraise=True
    )
    def get_historical_data(self, stock: str, interval_in_minutes: int, start_time: str, end_time: str) -> pd.DataFrame:
        cache_key = f"{stock}_{interval_in_minutes}_{start_time}_{end_time}"
        now = datetime.now()
        if cache_key in self._cache and (now - self._cache[cache_key]["timestamp"]) < self._cache_expiry:
            return self._cache[cache_key]["data"]
        try:
            data = self._data_provider.fetch_historical_data(stock, interval_in_minutes, start_time, end_time)
            if data.empty:
                logging.warning(f"Empty data for {stock}")
            self._cache[cache_key] = {"timestamp": now, "data": data}
            return data
        except Exception as e:
            logging.error(f"Data fetch failed for {stock}: {e}")
            raise  # Reraise for retry

    def get_multiple_stocks_data(self, stocks: list[str], interval_in_minutes: int, start_time: str, end_time: str) -> dict[str, pd.DataFrame]:
        all_data = {}
        batch_size = 5  # Process in batches to avoid rate limits
        for i in range(0, len(stocks), batch_size):
            batch = stocks[i:i + batch_size]
            for stock in batch:
                all_data[stock] = self.get_historical_data(stock, interval_in_minutes, start_time, end_time)
                time.sleep(10)  # Increased delay per stock to 10s
            time.sleep(30)  # Additional delay per batch
        return all_data

    def get_ltp(self, stock: str) -> float:
        return self._data_provider.get_ltp(stock)

logging.basicConfig(level=logging.INFO)
