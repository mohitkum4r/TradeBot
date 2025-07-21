# infrastructure/brokers/groww_broker.py
from typing import Optional, Any
from growwapi import GrowwAPI
from growwapi.groww.exceptions import GrowwAPIException
from tenacity import retry, stop_after_attempt, wait_exponential
import logging
from domain.models.trade import Trade


class GrowwBrokerClient:
    def __init__(self, client: GrowwAPI):
        self.client = client

    @classmethod
    def from_access_token(cls, access_token: str) -> "GrowwBrokerClient":
        client = GrowwAPI(token=access_token)
        return cls(client)

    def place_order(self, trade: Trade) -> dict[str, Any]:
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=10),
        )
        def _place():
            try:
                return self.client.place_order(
                    trading_symbol=trade.stock,
                    quantity=trade.quantity,
                    transaction_type=trade.action.upper(),
                    exchange="NSE",
                    segment="EQUITY",
                    product="REGULAR",
                    order_type="MARKET",
                    validity="DAY",
                    price=trade.price if trade.price else None,
                    trigger_price=None,
                    order_reference_id=trade.order_id if trade.order_id else None,
                )
            except GrowwAPIException as e:
                logging.error(f"Order placement failed: {e}")
                raise

        return _place()

    def get_all_orders(
        self, segment: Optional[str] = None, page: int = 0, page_size: int = 100
    ) -> dict[str, Any]:
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=10),
        )
        def _get():
            try:
                return self.client.get_order_list(
                    segment=segment, page=page, page_size=page_size
                )
            except GrowwAPIException as e:
                logging.error(f"Get orders failed: {e}")
                raise

        return _get()

    def get_ltp(self, stock: str) -> float:
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=4, max=10),
        )
        def _get_ltp():
            try:
                ltp_data = self.client.get_ltp(
                    exchange_trading_symbols=(f"NSE:{stock}",), segment="EQUITY"
                )
                return float(ltp_data.get(stock, {}).get("ltp", 0))
            except GrowwAPIException as e:
                logging.error(f"LTP fetch failed for {stock}: {e}")
                raise

        try:
            return _get_ltp()
        except Exception:
            return 0.0

    # Implement other methods similarly with retries
    def get_account_details(self) -> dict:
        # Assuming Groww has a method; placeholder if not
        return self.client.get_available_margin_details()  # Example

    def cancel_order(self, order_id: str) -> dict:
        # Assuming a cancel method; implement based on docs
        pass  # Placeholder: return self.client.cancel_order(order_id=order_id)


logging.basicConfig(level=logging.INFO)
