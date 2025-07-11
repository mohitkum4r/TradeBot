from ..config import Config


def calculate_taxes(transaction_value: float, action: str) -> float:
    """
    Calculates approximate taxes for an equity trade in the Indian market.
    This is a simplified calculation for CNC trades.
    """
    if transaction_value <= 0:
        return 0.0

    stt: float = 0.0
    stamp_duty: float = 0.0

    if action.upper() == "BUY":
        # Stamp duty is on the buy side
        stamp_duty = transaction_value * Config.STAMP_DUTY
    elif action.upper() == "SELL":
        # STT is on the sell side for delivery
        stt = transaction_value * Config.STT_CHARGE

    transaction_charge = transaction_value * Config.TRANSACTION_CHARGE
    gst = transaction_charge * Config.GST_ON_TRANSACTION_CHARGE
    sebi_fees = transaction_value * Config.SEBI_CHARGE

    total_taxes = stt + transaction_charge + gst + sebi_fees + stamp_duty
    return total_taxes
