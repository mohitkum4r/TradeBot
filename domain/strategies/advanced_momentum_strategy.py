# domain/strategies/advanced_momentum_strategy.py
import pandas as pd
import logging
from typing import List, Tuple, Dict, Any
from .base_strategy import BaseStrategy
from app.config import Config

logging.basicConfig(level=logging.INFO)

class AdvancedMomentumStrategy(BaseStrategy):
    def __init__(
        self,
        stock_universe: list[str] = Config.STOCKS,
        lookback_period: int = 126,  # Optimized for 6 months
        top_percentile: float = 0.1,
    ):
        self.stock_universe = stock_universe
        self.lookback_period = lookback_period
        self.top_n = int(len(stock_universe) * top_percentile)

    def generate_signal(
        self, data: Dict[str, pd.DataFrame], **kwargs: Any
    ) -> List[Tuple[str, str, str, Dict[str, float]]]:
        current_portfolio = kwargs.get("current_portfolio", [])
        momentum_scores = {}
        for stock, stock_data in data.items():
            if len(stock_data) >= self.lookback_period:
                momentum = (stock_data["close"].iloc[-1] / stock_data["close"].iloc[-self.lookback_period]) - 1
                momentum_scores[stock] = momentum
            else:
                logging.warning(f"Insufficient data for {stock}")

        if not momentum_scores:
            return [("", "HOLD", "No momentum scores calculated", {})]

        ranked_stocks = sorted(momentum_scores.items(), key=lambda item: item[1], reverse=True)
        winner_portfolio = [stock for stock, score in ranked_stocks[: self.top_n]]

        trades = []
        for stock in current_portfolio:
            if stock not in winner_portfolio:
                extras = {"stop_loss": data[stock]["close"].iloc[-1] * 0.98, "take_profit": data[stock]["close"].iloc[-1] * 1.05}
                trades.append((stock, "SELL", "Dropped from top momentum ranking.", extras))
        for stock in winner_portfolio:
            if stock not in current_portfolio:
                extras = {"stop_loss": data[stock]["close"].iloc[-1] * 0.98, "take_profit": data[stock]["close"].iloc[-1] * 1.05}
                trades.append((stock, "BUY", "Entered top momentum ranking.", extras))
        return trades if trades else [("", "HOLD", "No trades needed", {})]
