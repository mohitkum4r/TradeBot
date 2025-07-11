# autotrade/services/trade_executor.py
from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from ..config import Config
from .. import models
from . import tax_calculator
from .data_handler import DataHandler
from growwapi import GrowwAPI
from growwapi.groww.exceptions import GrowwAPIException
from tenacity import retry, stop_after_attempt, wait_exponential


class BaseTradeExecutor(ABC):
    def __init__(
        self, db: Session, data_handler: DataHandler, client: GrowwAPI | None = None
    ):
        self.db = db
        self.data_handler = data_handler
        self.client = client

    @abstractmethod
    def execute_trade(
        self, stock: str, signal: str, quantity: int, reason: str, capital: float
    ):
        pass

    def _apply_risk_management(
        self, price: float, quantity: int, capital: float
    ) -> int:
        risk_amount = capital * Config.RISK_PER_TRADE
        stop_loss_price = price * (1 - Config.STOP_LOSS_PCT)
        position_size = int(risk_amount / (price - stop_loss_price))
        return min(quantity, position_size)  # Cap at calculated size

    def _log_and_update_portfolio(
        self,
        action,
        stock,
        qty,
        price,
        reason,
        order_id,
        taxes,
        pnl=0.0,
        status="EXECUTED",
    ):
        # Log the trade
        trade_log = models.TradeLog(
            groww_order_id=order_id,
            stock=stock,
            action=action,
            price=price,
            quantity=qty,
            total_cost=(price * qty),
            profit_loss=pnl,
            taxes=taxes,
            reason=reason,
            mode=Config.MODE,
            status=status,
        )
        self.db.add(trade_log)

        # Update portfolio table
        item = (
            self.db.query(models.Portfolio)
            .filter(models.Portfolio.stock == stock)
            .first()
        )
        if action == "BUY":
            if item:
                new_cost = (item.average_price * item.quantity) + (price * qty)
                new_qty = item.quantity + qty
                item.average_price = new_cost / new_qty if new_qty > 0 else 0
                item.quantity = new_qty
            else:
                self.db.add(
                    models.Portfolio(stock=stock, quantity=qty, average_price=price)
                )
        elif action == "SELL":
            if item:
                item.quantity -= qty
                if item.quantity <= 0:
                    self.db.delete(item)

        self.db.commit()
        print(
            f"-> {action} for {qty} of {stock} was successful. Portfolio and logs updated."
        )


class LiveTradeExecutor(BaseTradeExecutor):
    @retry(
        stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def execute_trade(
        self, stock: str, signal: str, quantity: int, reason: str, capital: float
    ):
        if quantity <= 0:
            print(f"Skipping trade for {stock}: Invalid quantity ({quantity}).")
            return

        ltp = self.data_handler.get_ltp(stock)
        if not ltp:
            print(f"Could not execute trade for {stock}, failed to get LTP.")
            return

        quantity = self._apply_risk_management(ltp, quantity, capital)

        if signal == "BUY":
            self._execute_buy(stock, quantity, ltp, reason)
        elif signal == "SELL":
            self._execute_sell(stock, quantity, ltp, reason)

        # Check for SL/TP (simplified; in production, use order monitoring)
        # Note: Groww API may require separate orders for SL/TP

    def _execute_buy(self, stock, quantity, price, reason):
        total_cost = price * quantity
        taxes = tax_calculator.calculate_taxes(total_cost, "BUY")

        print(f"--- PLACING LIVE BUY ORDER for {quantity} of {stock} ---")
        try:
            limit_price = round(price * 1.002, 1)  # 0.2% buffer

            response = self.client.place_order(
                trading_symbol=stock,
                quantity=quantity,
                price=limit_price,
                validity=self.client.VALIDITY_DAY,
                exchange=self.client.EXCHANGE_NSE,
                segment=self.client.SEGMENT_CASH,
                product=self.client.PRODUCT_CNC,
                order_type=self.client.ORDER_TYPE_LIMIT,
                transaction_type=self.client.TRANSACTION_TYPE_BUY,
            )
            order_id = response.get("groww_order_id")
            print(f"LIVE BUY successful. Order ID: {order_id}")
            self._log_and_update_portfolio(
                "BUY", stock, quantity, price, reason, order_id, taxes
            )
        except GrowwAPIException as e:
            print(f"!!! LIVE BUY FAILED for {stock}: {e} !!!")
            self._log_and_update_portfolio(
                "BUY", stock, quantity, price, reason, None, taxes, status="FAILED"
            )
            raise

    def _execute_sell(self, stock, quantity, price, reason):
        portfolio_item = (
            self.db.query(models.Portfolio)
            .filter(models.Portfolio.stock == stock)
            .first()
        )
        if not portfolio_item or portfolio_item.quantity < quantity:
            print(f"SELL FAILED for {stock}: Not enough shares in portfolio.")
            return

        print(f"--- PLACING LIVE SELL ORDER for {quantity} of {stock} ---")
        try:
            limit_price = round(price * 0.998, 1)  # 0.2% buffer

            response = self.client.place_order(
                trading_symbol=stock,
                quantity=quantity,
                price=limit_price,
                validity=self.client.VALIDITY_DAY,
                exchange=self.client.EXCHANGE_NSE,
                segment=self.client.SEGMENT_CASH,
                product=self.client.PRODUCT_CNC,
                order_type=self.client.ORDER_TYPE_LIMIT,
                transaction_type=self.client.TRANSACTION_TYPE_SELL,
            )
            order_id = response.get("groww_order_id")
            print(f"LIVE SELL successful. Order ID: {order_id}")

            total_sale_value = price * quantity
            cost_of_sold_shares = portfolio_item.average_price * quantity
            pnl = total_sale_value - cost_of_sold_shares
            taxes = tax_calculator.calculate_taxes(total_sale_value, "SELL")

            self._log_and_update_portfolio(
                "SELL", stock, quantity, price, reason, order_id, taxes, pnl
            )
        except GrowwAPIException as e:
            print(f"!!! LIVE SELL FAILED for {stock}: {e} !!!")
            self._log_and_update_portfolio(
                "SELL", stock, quantity, price, reason, None, 0.0, 0.0, status="FAILED"
            )
            raise


class PaperTradeExecutor(BaseTradeExecutor):
    def execute_trade(
        self, stock: str, signal: str, quantity: int, reason: str, capital: float
    ):
        if quantity <= 0:
            print(f"Skipping trade for {stock}: Invalid quantity ({quantity}).")
            return

        ltp = self.data_handler.get_ltp(stock)
        if not ltp:
            print(f"Could not execute paper trade for {stock}, failed to get LTP.")
            return

        quantity = self._apply_risk_management(ltp, quantity, capital)

        if signal == "BUY":
            print(f"EXECUTING PAPER BUY: {quantity} of {stock} @ ₹{ltp:.2f}")
            total_cost = ltp * quantity
            taxes = tax_calculator.calculate_taxes(total_cost, "BUY")
            self._log_and_update_portfolio(
                "BUY", stock, quantity, ltp, reason, f"PAPER_{stock}_BUY", taxes
            )
        elif signal == "SELL":
            portfolio_item = (
                self.db.query(models.Portfolio)
                .filter(models.Portfolio.stock == stock)
                .first()
            )
            if not portfolio_item or portfolio_item.quantity < quantity:
                print(f"PAPER SELL FAILED for {stock}: Not enough shares in portfolio.")
                return

            print(f"EXECUTING PAPER SELL: {quantity} of {stock} @ ₹{ltp:.2f}")
            total_sale_value = ltp * quantity
            cost_of_sold_shares = portfolio_item.average_price * quantity
            pnl = total_sale_value - cost_of_sold_shares
            taxes = tax_calculator.calculate_taxes(total_sale_value, "SELL")
            self._log_and_update_portfolio(
                "SELL", stock, quantity, ltp, reason, f"PAPER_{stock}_SELL", taxes, pnl
            )
