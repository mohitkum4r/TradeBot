# autotrade/strategies/statistical_arbitrage_strategy.py
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint
from .base_strategy import BaseStrategy


class StatisticalArbitrageStrategy(BaseStrategy):
    """
    Enhanced pairs trading for statistical arbitrage. Scans for cointegrated pairs.
    (Template for cash-futures arbitrage; extend for futures data.)
    """

    def __init__(self, pairs_list: list[list[str]], window=60, entry_z=2.0):
        self.pairs_list = pairs_list
        self.window = window
        self.entry_z = entry_z

    def generate_signal(self, data: pd.DataFrame) -> tuple[str, str, str]:
        # Handle multi-index DataFrame by selecting 'close' level
        if isinstance(data.columns, pd.MultiIndex):
            close_data = data.xs('close', level=1, axis=1)
        else:
            close_data = data

        best_pair = None
        best_z = 0

        for pair in self.pairs_list:
            stock1, stock2 = pair
            if stock1 not in close_data.columns or stock2 not in close_data.columns:
                continue

            pair_data = pd.concat([close_data[stock1], close_data[stock2]], axis=1).dropna()
            if len(pair_data) < self.window:
                continue

            _, p_value, _ = coint(pair_data[stock1], pair_data[stock2])
            if p_value < 0.05:
                x = sm.add_constant(pair_data[stock2])
                model = sm.OLS(pair_data[stock1], x).fit()
                spread = pair_data[stock1] - model.params[1] * pair_data[stock2]
                z_score = (
                    (spread.iloc[-1] - spread.mean()) / spread.std()
                )

                if abs(z_score) > abs(best_z):
                    best_z = z_score
                    best_pair = (stock1, stock2)

        if not best_pair:
            return "HOLD", "", "No arbitrage opportunity."

        stock1, stock2 = best_pair
        if best_z > self.entry_z:
            return "SELL_SPREAD", f"{stock1},{stock2}", f"Arbitrage: Short {stock1}, Long {stock2}"
        if best_z < -self.entry_z:
            return "BUY_SPREAD", f"{stock1},{stock2}", f"Arbitrage: Long {stock1}, Short {stock2}"

        return "HOLD", "", "No signal."