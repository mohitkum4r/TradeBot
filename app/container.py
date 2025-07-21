# app/container.py
import logging
from typing import Dict, Type, Callable

from app.config import Config
from infrastructure.data_providers.data_handler import DataHandler
from infrastructure.database.sqlite_trade_logger import SQLiteTradeLogger
from infrastructure.ml.ml_predictor import MLPredictor
from infrastructure.sentiment.sentiment_analyzer import SentimentAnalyzer
from infrastructure.tax.tax_calculator import TaxCalculator
from infrastructure.stock_screener.stock_screener import StockScreener
from interfaces.i_data_provider import IDataProvider
from interfaces.i_trade_logger import ITradeLogger
from interfaces.i_sentiment_analyzer import ISentimentAnalyzer
from interfaces.i_tax_calculator import ITaxCalculator

class Container:
    def __init__(self):
        self._dependencies: Dict[Type, Callable] = {}
        self._instances: Dict[Type, object] = {}

    def register(self, interface: Type, implementation: Callable):
        self._dependencies[interface] = implementation

    def get(self, interface: Type) -> object:
        if interface not in self._instances:
            if interface not in self._dependencies:
                raise ValueError(f"No registration for {interface}")
            self._instances[interface] = self._dependencies[interface](self)
        return self._instances[interface]

    def register_defaults(self):
        self.register(ITradeLogger, lambda c: SQLiteTradeLogger())
        self.register(MLPredictor, lambda c: MLPredictor())
        self.register(ISentimentAnalyzer, lambda c: SentimentAnalyzer())
        self.register(ITaxCalculator, lambda c: TaxCalculator())
        self.register(DataHandler, lambda c: DataHandler(data_provider=c.get(IDataProvider)))  # Register DataHandler with dependency
        self.register(StockScreener, lambda c: StockScreener(data_handler=c.get(DataHandler), stocks=Config.STOCKS))

container = Container()
container.register_defaults()  # Register non-client-dependent first
logging.basicConfig(level=logging.INFO)
