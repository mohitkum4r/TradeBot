# domain/strategies/dynamic_pairs_strategy.py
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint
import logging
from typing import List, Tuple, Dict, Any
from .base_strategy import BaseStrategy

logging.basicConfig(level=logging.INFO)

class DynamicPairsStrategy(BaseStrategy):
    def __init__(
        self, pairs_list: list[list[str]], window: int = 60, entry_z: float = 2.0
    ):
        self.pairs_list = pairs_list
        self.window = window
        self.entry_z = entry_z

    def generate_signal(
        self, data: Dict[str, pd.DataFrame], **kwargs: Any
    ) -> List[Tuple[str, str, str, Dict[str, float]]]:
        # Combine all stock data into one DF for pairs
        all_close = pd.concat([df["close"].rename(stock) for stock, df in data.items()], axis=1)
        best_pair = None
        highest_z = 0
        for pair in self.pairs_list:
            stock1, stock2 = pair[0], pair[1]
            if stock1 not in all_close or stock2 not in all_close:
                continue
            pair_data = all_close[[stock1, stock2]].dropna()
            if len(pair_data) < self.window:
                continue
            _, p_value, _ = coint(pair_data[stock1], pair_data[stock2])
            if p_value < 0.05:
                x = sm.add_constant(pair_data[stock2])
                model = sm.OLS(pair_data[stock1], x).fit()
                spread = pair_data[stock1] - model.params[1] * pair_data[stock2]
                z_score = ((spread.iloc[-1] - spread.rolling(self.window).mean().iloc[-1]) / spread.rolling(self.window).std().iloc[-1]) if spread.rolling(self.window).std().iloc[-1] != 0 else 0
                if abs(z_score) > abs(highest_z):
                    highest_z = z_score
                    best_pair = (stock1, stock2)

        if not best_pair:
            return [("", "HOLD", "No suitable cointegrated pair found.", {})]

        stock1, stock2 = best_pair
        instrument = f"{stock1},{stock2}"
        last_price1 = data[stock1]["close"].iloc[-1] if stock1 in data else 0
        extras = {"stop_loss": last_price1 * 0.98, "take_profit": last_price1 * 1.05}  # Example for stock1
        if highest_z > self.entry_z:
            return [(instrument, "SELL_SPREAD", f"Z-score {highest_z:.2f} > {self.entry_z}", extras)]
        if highest_z < -self.entry_z:
            return [(instrument, "BUY_SPREAD", f"Z-score {highest_z:.2f} < -{self.entry_z}", extras)]
        return [(instrument, "HOLD", f"Z-score {highest_z:.2f} within threshold.", {})]
