# domain/models/trade.py
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Trade:
    timestamp: datetime
    stock: str
    action: str
    price: float
    quantity: int
    reason: str
    order_id: str = ""
    pnl: float = 0.0
    taxes: float = 0.0
    status: str = "PENDING"

    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.price <= 0:
            raise ValueError("Price must be positive")
        if self.action not in ["BUY", "SELL"]:
            raise ValueError("Action must be BUY or SELL")
