# interfaces/i_data_provider.py
from abc import ABC, abstractmethod
import pandas as pd

class IDataProvider(ABC):
    @abstractmethod
    def fetch_historical_data(
        self, stock: str, interval_in_minutes: int, start_time: str, end_time: str
    ) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_ltp(self, stock: str) -> float:
        pass
