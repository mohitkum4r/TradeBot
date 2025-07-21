# interfaces/i_broker_client.py
from abc import ABC, abstractmethod
from domain.models.trade import Trade


class IBrokerClient(ABC):
    @abstractmethod
    def get_account_details(self) -> dict:
        pass

    @abstractmethod
    def get_all_orders(self) -> list[dict]:
        pass

    @abstractmethod
    def place_order(self, trade: Trade) -> dict:
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> dict:
        pass

    @abstractmethod
    def get_ltp(self, stock: str) -> float:
        pass
