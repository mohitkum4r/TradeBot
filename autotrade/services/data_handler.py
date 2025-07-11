import pandas as pd
from datetime import datetime, timedelta
from growwapi import GrowwAPI
from growwapi.groww.exceptions import GrowwAPIException
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError


class DataHandler:
    def __init__(self, client: GrowwAPI):
        self.client = client

    @retry(
        stop=stop_after_attempt(4),  # Increased attempts
        wait=wait_exponential(multiplier=1.5, min=3, max=15) # Increased wait with jitter
    )
    def get_historical_data(
        self, stock: str, days: int = 90, interval_minutes: int = 60
    ) -> pd.DataFrame:
        print(f"Fetching historical data for {stock}...")
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
            print(f"API Error fetching historical data for {stock}: {e}")
            raise  # Re-raise for retry logic
        except Exception as e:
            print(f"An unexpected error occurred fetching historical data for {stock}: {e}")
            return pd.DataFrame() # Return empty df on non-retryable error

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def get_ltp(self, stock: str) -> float | None:
        print(f"Fetching LTP for {stock}...")
        try:
            # Assuming the API requires NSE prefix for cash segment
            symbol_to_fetch = f"NSE_{stock.upper()}"
            response = self.client.get_ltp(
                segment=self.client.SEGMENT_CASH, exchange_trading_symbols=(symbol_to_fetch,)
            )

            ltp = response.get(symbol_to_fetch)
            if ltp:
                print(f"LTP for {stock}: {ltp}")
                return float(ltp)
            else:
                print(f"LTP not found for {stock} in API response.")
                return None

        except GrowwAPIException as e:
            print(f"API Error fetching LTP for {stock}: {e}")
            raise  # Re-raise for retry
        except Exception as e:
            print(f"An unexpected error occurred fetching LTP for {stock}: {e}")
            return None