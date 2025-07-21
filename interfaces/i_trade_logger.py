from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from domain.models.trade import Trade


class ITradeLogger(ABC):
    @abstractmethod
    def log_trade(self, db: Session, trade: Trade):
        pass
