import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint
from .base_strategy import BaseStrategy
from ..config import Config

# NEW: Enhanced Arbitrage Strategy with hedging for profit maximization
class EnhancedArbitrageStrategy(BaseStrategy):
    """
    Scans for cointegrated pairs and adds hedging if spread widens.
    """

    def __init__(self, pairs_list: list[list[str]], window=60, entry_z=Config.ENTRY_Z, hedge_threshold=Config.HEDGE_THRESHOLD):
        self.pairs_list = pairs_list
        self.window = window
        self.entry_z = entry_z
        self.hedge_threshold = hedge_threshold

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
                spread = pair_data[stock1] - model.params.iloc[1] * pair_data[stock2]  # Use iloc for params
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
            return "SELL_SPREAD", f"{stock1},{stock2}", f"Arbitrage: Short {stock1}, Long {stock2} (Z: {best_z:.2f})"
        if best_z < -self.entry_z:
            return "BUY_SPREAD", f"{stock1},{stock2}", f"Arbitrage: Long {stock1}, Short {stock2} (Z: {best_z:.2f})"

        # NEW: Hedge if spread widens beyond threshold (for profit protection)
        if abs(best_z) > self.entry_z * (1 + self.hedge_threshold):
            return "HEDGE", f"{stock1},{stock2}", f"Hedging: Close spread due to widening (Z: {best_z:.2f})"

        return "HOLD", "", "No signal."