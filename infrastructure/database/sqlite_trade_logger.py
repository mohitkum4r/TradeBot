# infrastructure/database/sqlite_trade_logger.py
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from domain.models.models import TradeLog
from domain.models.trade import Trade
from interfaces.i_trade_logger import ITradeLogger
from app.config import Config


class SQLiteTradeLogger(ITradeLogger):
    def __init__(self, db_url: str = Config.DATABASE_URL):
        self.engine = create_engine(db_url)
        self.logger = logging.getLogger(__name__)

    def log_trade(self, db: Session, trade: Trade) -> None:
        try:
            trade_log = TradeLog(
                timestamp=trade.timestamp,
                groww_order_id=trade.order_id,
                stock=trade.stock,
                action=trade.action,
                price=trade.price,
                quantity=trade.quantity,
                total_cost=trade.price * trade.quantity,
                profit_loss=trade.pnl,
                taxes=trade.taxes,
                reason=trade.reason,
                mode=Config.MODE,
                status=trade.status,
            )
            db.add(trade_log)
            db.commit()
            self.logger.info(f"Logged trade for {trade.stock}")
        except Exception as e:
            db.rollback()
            self.logger.error(f"Logging failed: {e}")
            raise


logging.basicConfig(level=logging.INFO)
