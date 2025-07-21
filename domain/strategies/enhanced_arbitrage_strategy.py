# domain/strategies/enhanced_arbitrage_strategy.py
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint
import logging
from typing import List, Tuple, Dict, Any
from .base_strategy import BaseStrategy
from app.config import Config

logging.basicConfig(level=logging.INFO)

class EnhancedArbitrageStrategy(BaseStrategy):
    def __init__(
        self,
        pairs_list: list[list[str]],
        window=60,
        entry_z=Config.ENTRY_Z,
        hedge_threshold=Config.HEDGE_THRESHOLD,
    ):
        self.pairs_list = pairs_list
        self.window = window
        self.entry_z = entry_z
        self.hedge_threshold = hedge_threshold

    def generate_signal(
        self, data: Dict[str, pd.DataFrame], **kwargs: Any
    ) -> List[Tuple[str, str, str, Dict[str, float]]]:
        all_close = pd.concat([df["close"].rename(stock) for stock, df in data.items()], axis=1)
        best_pair = None
        best_z = 0
        for pair in self.pairs_list:
            stock1, stock2 = pair
            if stock1 not in all_close or stock2 not in all_close:
                continue
            pair_data = all_close[[stock1, stock2]].dropna()
            if len(pair_data) < self.window:
                continue
            _, p_value, _ = coint(pair_data[stock1], pair_data[stock2])
            if p_value < 0.05:
                x = sm.add_constant(pair_data[stock2])
                model = sm.OLS(pair_data[stock1], x).fit()
                spread = pair_data[stock1] - model.params.iloc[1] * pair_data[stock2]
                z_score = (spread.iloc[-1] - spread.mean()) / spread.std()
                if abs(z_score) > abs(best_z):
                    best_z = z_score
                    best_pair = (stock1, stock2)

        if not best_pair:
            return [("", "HOLD", "No arbitrage opportunity.", {})]

        stock1, stock2 = best_pair
        instrument = f"{stock1},{stock2}"
        last_price1 = data[stock1]["close"].iloc[-1] if stock1 in data else 0
        extras = {"stop_loss": last_price1 * 0.98, "take_profit": last_price1 * 1.05}
        if best_z > self.entry_z:
            return [(instrument, "SELL_SPREAD", f"Short {stock1}, Long {stock2} (Z: {best_z:.2f})", extras)]
        if best_z < -self.entry_z:
            return [(instrument, "BUY_SPREAD", f"Long {stock1}, Short {stock2} (Z: {best_z:.2f})", extras)]
        if abs(best_z) > self.entry_z * (1 + self.hedge_threshold):
            return [(instrument, "HEDGE", f"Close spread due to widening (Z: {best_z:.2f})", extras)]
        return [("", "HOLD", "No signal.", {})]
