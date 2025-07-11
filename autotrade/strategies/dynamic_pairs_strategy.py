import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint
from .base_strategy import BaseStrategy


class DynamicPairsStrategy(BaseStrategy):
    """
    Scans a list of potential pairs, finds the best cointegrated pair
    in the current market, and generates a trading signal for it.
    """

    def __init__(self, pairs_list: list[list[str]], window=60, entry_z=2.0):
        self.pairs_list = pairs_list
        self.window = window
        self.entry_z = entry_z

    def find_best_pair(self, data: pd.DataFrame) -> tuple[str | None, float]:
        """Finds the cointegrated pair with the highest Z-score."""
        best_pair = None
        highest_z = 0

        for pair in self.pairs_list:
            stock1, stock2 = pair[0], pair[1]
            if stock1 not in data.columns or stock2 not in data.columns:
                continue

            pair_data = data[[stock1, stock2]].dropna()
            if len(pair_data) < self.window:
                continue

            # Test for cointegration
            _, p_value, _ = coint(pair_data[stock1], pair_data[stock2])
            if p_value < 0.05:  # If cointegrated
                # Calculate Z-score
                x = sm.add_constant(pair_data[stock2])
                y = pair_data[stock1]
                model = sm.OLS(y, x).fit()
                spread = y - model.params[1] * pair_data[stock2]
                z_score = (
                    spread.iloc[-1] - spread.rolling(window=self.window).mean().iloc[-1]
                ) / spread.rolling(window=self.window).std().iloc[-1]

                if abs(z_score) > abs(highest_z):
                    highest_z = z_score
                    best_pair = (stock1, stock2)

        return best_pair, highest_z

    def generate_signal(self, data: pd.DataFrame) -> tuple[str, str, str]:
        """
        Args:
            data (pd.DataFrame): DataFrame containing close prices for ALL stocks in the pairs list.
        """
        best_pair, z_score = self.find_best_pair(data)

        if not best_pair:
            return "HOLD", "", "No suitable cointegrated pair found."

        stock1, stock2 = best_pair

        # Generate signal for the best pair found
        if z_score > self.entry_z:
            return (
                "SELL_SPREAD",
                f"{stock1},{stock2}",
                f"Z-score ({z_score:.2f}) > {self.entry_z}",
            )

        if z_score < -self.entry_z:
            return (
                "BUY_SPREAD",
                f"{stock1},{stock2}",
                f"Z-score ({z_score:.2f}) < -{self.entry_z}",
            )

        return (
            "HOLD",
            "",
            f"Best pair ({stock1},{stock2}) Z-score ({z_score:.2f}) is within threshold.",
        )
