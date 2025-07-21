# infrastructure/tax/tax_calculator.py
from domain.models.trade import Trade
from interfaces.i_tax_calculator import ITaxCalculator
from app.config import Config
import logging


class TaxCalculator(ITaxCalculator):
    def calculate_taxes(self, trade: Trade) -> float:
        if trade.quantity <= 0 or trade.price <= 0:
            # logging.warning("Invalid trade for tax calc")
            return 0.0
        turnover = trade.price * trade.quantity
        stt = turnover * Config.STT_CHARGE if trade.action == "SELL" else 0
        txn_charge = turnover * Config.TRANSACTION_CHARGE
        gst = txn_charge * Config.GST_ON_TRANSACTION_CHARGE
        sebi_fees = turnover * Config.SEBI_CHARGE
        stamp_duty = turnover * Config.STAMP_DUTY if trade.action == "BUY" else 0
        total = stt + txn_charge + gst + sebi_fees + stamp_duty
        # logging.info(f"Taxes for {trade.stock}: {total:.2f}")
        return total

logging.basicConfig(level=logging.INFO)
