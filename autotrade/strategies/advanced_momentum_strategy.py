import pandas as pd
from .base_strategy import BaseStrategy


class AdvancedMomentumStrategy(BaseStrategy):
    """
    A portfolio-level momentum strategy that ranks a universe of stocks
    and rotates into the top performers periodically.
    Source: Algorithmic Trading NSE Strategies_.docx [cite: 171]
    """

    def __init__(
        self, stock_universe: list[str], lookback_period=126, top_percentile=0.1
    ):
        """
        Args:
            stock_universe (list[str]): The list of all stocks to consider.
            lookback_period (int): The number of trading days to measure momentum (approx. 6 months).
            top_percentile (float): The percentage of top stocks to hold (e.g., 0.1 for top 10%).
        """
        self.stock_universe = stock_universe
        self.lookback_period = lookback_period
        self.top_n = int(len(stock_universe) * top_percentile)

    def generate_signal(
        self, data: pd.DataFrame, current_portfolio: list[str]
    ) -> list[tuple[str, str, str]]:
        """
        Analyzes the entire universe and returns a list of trades to rebalance the portfolio.

        Args:
            data (pd.DataFrame): A DataFrame with multi-column headers,
                                 where the first level is the stock symbol.
            current_portfolio (list[str]): A list of stocks currently held.

        Returns:
            list[tuple[str, str, str]]: A list of (Stock, Signal, Reason) tuples.
        """
        momentum_scores = {}
        for stock in self.stock_universe:
            if stock in data.columns:
                stock_data = data[stock]
                if len(stock_data) >= self.lookback_period:
                    # Calculate the return over the lookback period
                    momentum = (
                        stock_data["close"].iloc[-1]
                        / stock_data["close"].iloc[-self.lookback_period]
                    ) - 1
                    momentum_scores[stock] = momentum

        if not momentum_scores:
            return []

        # Rank stocks by momentum
        ranked_stocks = sorted(
            momentum_scores.items(), key=lambda item: item[1], reverse=True
        )

        # Identify the new "winner" portfolio
        winner_portfolio = [stock for stock, score in ranked_stocks[: self.top_n]]

        trades = []
        # Generate SELL signals for stocks that are no longer winners
        for stock in current_portfolio:
            if stock not in winner_portfolio:
                trades.append((stock, "SELL", "Dropped from top momentum ranking."))

        # Generate BUY signals for new winners
        for stock in winner_portfolio:
            if stock not in current_portfolio:
                trades.append((stock, "BUY", "Entered top momentum ranking."))

        return trades