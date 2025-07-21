# infrastructure/stock_screener/stock_screener.py
import logging
from utilities.date_utils import parse_screening_dates
import pandas as pd
from infrastructure.data_providers.data_handler import DataHandler

logging.basicConfig(level=logging.INFO)

class StockScreener:
    def __init__(self, data_handler: DataHandler, stocks: list[str]):
        self.data_handler = data_handler
        self.stocks = stocks

    def screen_for_momentum(self) -> list[str]:
        momentum_stocks = []
        start_time, end_time = parse_screening_dates(90)  # Use utility to avoid duplicacy
        for stock in self.stocks:
            try:
                data = self.data_handler.get_historical_data(stock, 1440, start_time, end_time)  # 1-day interval (1440 min)
                if isinstance(data, pd.Series):
                    data = data.to_frame(name="close")  # Convert Series to DataFrame if needed
                if data.empty or len(data) < 21:
                    logging.warning(f"Insufficient or empty data for {stock}")
                    continue
                data["ma20"] = data["close"].rolling(window=20).mean()
                if pd.isna(data["ma20"].iloc[-1]):
                    continue
                if data["close"].iloc[-1] > data["ma20"].iloc[-1]:
                    momentum_stocks.append(stock)
            except Exception as e:
                logging.error(f"Error screening {stock}: {e}")
        if not momentum_stocks:
            logging.warning("No momentum stocks found; using all stocks as fallback.")
            return self.stocks  # Fallback to avoid empty list
        return momentum_stocks
