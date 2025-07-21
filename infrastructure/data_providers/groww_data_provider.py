# infrastructure/data_providers/groww_data_provider.py
import pandas as pd
from growwapi import GrowwAPI
from interfaces.i_data_provider import IDataProvider
import logging
from datetime import datetime


class GrowwDataProvider(IDataProvider):
    def __init__(self, client: GrowwAPI):
        self.client = client

    def fetch_historical_data(self, stock: str, interval_in_minutes: int, start_time: str,
                              end_time: str) -> pd.DataFrame:
        try:
            # Parse and reformat to 'yyyy-MM-dd HH:mm:ss' (e.g., '2025-04-20 00:00:00')
            start_dt = datetime.strptime(start_time, "%Y-%m-%d").strftime("%Y-%m-%d 00:00:00")
            end_dt = datetime.strptime(end_time, "%Y-%m-%d").strftime("%Y-%m-%d 23:59:59")  # End of day for full range

            raw_response = self.client.get_historical_candle_data(
                trading_symbol=stock, exchange="NSE", segment="CASH",
                start_time=start_dt, end_time=end_dt,
                interval_in_minutes=interval_in_minutes
            )

            # Extract 'candles' from response dict
            if not isinstance(raw_response, dict) or 'candles' not in raw_response:
                raise ValueError(f"Unexpected response format for {stock}: missing 'candles' key")

            candles = raw_response['candles']
            if not candles:
                logging.warning(f"No candles data for {stock}")
                return pd.DataFrame()

            # Create DataFrame from candles list [[timestamp, open, high, low, close, volume], ...]
            df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

            # Convert epoch timestamp (seconds) to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', utc=True).dt.tz_convert(
                'Asia/Kolkata')  # Adjust timezone if needed

            df.set_index('timestamp', inplace=True)
            return df
        except ValueError as ve:
            logging.error(f"Date format or value error for {stock}: {ve}")
            return pd.DataFrame()
        except Exception as e:
            logging.error(f"Historical data fetch failed for {stock}: {e}")
            return pd.DataFrame()

    def get_ltp(self, stock: str) -> float:
        try:
            ltp_data = self.client.get_ltp(exchange_trading_symbols=(f"NSE:{stock}",), segment="CASH")
            return float(ltp_data.get(stock, {}).get("ltp", 0))
        except Exception as e:
            logging.error(f"LTP fetch failed for {stock}: {e}")
            return 0.0


logging.basicConfig(level=logging.INFO)
