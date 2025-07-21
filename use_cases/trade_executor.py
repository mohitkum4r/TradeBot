# use_cases/trade_executor.py
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from interfaces.i_broker_client import IBrokerClient
from interfaces.i_trade_logger import ITradeLogger
from interfaces.i_tax_calculator import ITaxCalculator
from domain.models.trade import Trade
from app.config import Config
from infrastructure.data_providers.data_handler import DataHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class BaseTradeExecutor:
    def __init__(self, data_handler: DataHandler, logger: ITradeLogger, tax_calculator: ITaxCalculator):
        self.data_handler = data_handler
        self.logger = logger
        self.tax_calculator = tax_calculator

    def execute_trade(self, db_session: Session, stock: str, action: str, quantity: int, reason: str, current_capital: float):
        if quantity <= 0:
            logging.warning(f"Invalid quantity {quantity} for {stock}")
            return
        price = self.data_handler.get_ltp(stock)
        if price <= 0:
            logging.warning(f"Invalid price {price} for {stock}")
            return
        trade_value = price * quantity
        if trade_value > current_capital * Config.MAX_EXPOSURE_PER_TRADE:
            logging.warning(f"Trade exceeds exposure limit for {stock}")
            return

        trade = Trade(
            timestamp=datetime.now(),
            stock=stock,
            action=action,
            price=price,
            quantity=quantity,
            reason=reason
        )
        trade.taxes = self.tax_calculator.calculate_taxes(trade)
        self._execute_specific(trade)
        self.logger.log_trade(db_session, trade)
        logging.info(f"Executed {action} for {quantity} {stock} @ {price:.2f}")

    def _execute_specific(self, trade: Trade):
        raise NotImplementedError

class PaperTradeExecutor(BaseTradeExecutor):
    def _execute_specific(self, trade: Trade):
        trade.order_id = f"paper-{datetime.now().isoformat()}"
        trade.status = "PAPER_EXECUTED"
        logging.info(f"Paper {trade.action} simulated for {trade.stock}")

class LiveTradeExecutor(BaseTradeExecutor):
    def __init__(self, data_handler: DataHandler, logger: ITradeLogger, tax_calculator: ITaxCalculator, client: IBrokerClient):
        super().__init__(data_handler, logger, tax_calculator)
        self.client = client

    def _execute_specific(self, trade: Trade):
        if Config.MODE != "LIVE":
            raise ValueError("Cannot execute live trade in non-LIVE mode")
        confirm = input(f"Confirm LIVE {trade.action} for {trade.quantity} {trade.stock} (y/n): ")
        if confirm.lower() != 'y':
            logging.info("Live trade aborted")
            trade.status = "ABORTED"
            return
        order_result = self.client.place_order(trade)
        trade.order_id = order_result.get("orderId", "")
        trade.status = "EXECUTED" if trade.order_id else "FAILED"
