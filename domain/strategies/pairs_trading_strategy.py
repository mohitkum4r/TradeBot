# autotrade/strategies/pairs_trading_strategy.py

import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint
from .base_strategy import BaseStrategy


class PairsTradingStrategy(BaseStrategy):
    """
    A statistical arbitrage strategy based on cointegration.
    It identifies a stable, long-term relationship between two stocks and
    trades on the temporary deviations from that relationship (the "spread").
    Source: Algorithmic Trading NSE Strategies_.docx [cite: 1545, 1548]
    """

    def __init__(self, stock1: str, stock2: str, window=60, entry_z=2.0, exit_z=0.5):
        self.stock1 = stock1
        self.stock2 = stock2
        self.window = window
        self.entry_z = entry_z
        self.exit_z = exit_z

    def generate_signal(self, data: pd.DataFrame, **kwargs) -> tuple[str, str, str]:
        sentiment_score = kwargs.get("sentiment_score", 0.0)
        instrument = f"{self.stock1},{self.stock2}"
        if self.stock1 not in data.columns or self.stock2 not in data.columns:
            return (
                instrument,
                "HOLD",
                "Data for one or both stocks in the pair is missing.",
            )

        # 1. Test for cointegration to ensure a stable relationship exists [cite: 1557]
        _, p_value, _ = coint(data[self.stock1], data[self.stock2])
        if p_value > 0.05:
            return (
                instrument,
                "HOLD",
                f"Pair is not cointegrated (p-value: {p_value:.4f}).",
            )

        # 2. Calculate the spread and its Z-score [cite: 1560, 1561]
        x = sm.add_constant(data[self.stock2])
        y = data[self.stock1]
        model = sm.OLS(y, x).fit()
        spread = y - model.params[1] * data[self.stock2]

        mean = spread.rolling(window=self.window).mean()
        std = spread.rolling(window=self.window).std()
        z_score = (spread - mean) / std

        last_z = z_score.iloc[-1]

        # 3. Generate trading signals based on Z-score thresholds [cite: 1563]
        # Signal to short the spread (short stock1, long stock2)
        if last_z > self.entry_z:
            return (
                instrument,
                "SELL_SPREAD",
                f"Z-score ({last_z:.2f}) > {self.entry_z}. Shorting spread: short {self.stock1}, long {self.stock2}.",
            )

        # Signal to long the spread (long stock1, short stock2)
        if last_z < -self.entry_z:
            return (
                instrument,
                "BUY_SPREAD",
                f"Z-score ({last_z:.2f}) < -{self.entry_z}. Longing spread: long {self.stock1}, short {self.stock2}.",
            )

        # Exit signal when spread reverts to the mean
        if abs(last_z) < self.exit_z:
            return (
                instrument,
                "EXIT",
                f"Z-score ({last_z:.2f}) reverted to mean. Close position.",
            )

        return (
            instrument,
            "HOLD",
            f"Z-score ({last_z:.2f}) is within entry/exit thresholds.",
        )
