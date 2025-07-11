import pandas as pd
import numpy as np
from autotrade.strategies.base_strategy import BaseStrategy
from autotrade.services.data_handler import DataHandler
from autotrade.config import Config
from autotrade.services import tax_calculator


def run_backtest(strategy: BaseStrategy, data_handler: DataHandler):
    """
    Runs a more realistic backtest for a given strategy.
    """
    print(f"\n--- Starting backtest for strategy: {strategy.__class__.__name__} ---")

    # Use a single stock for backtesting for simplicity
    stock_symbol = Config.STOCKS[0] if Config.STOCKS else "RELIANCE"
    historical_df = data_handler.get_historical_data(
        stock_symbol, days=365, interval_minutes=60
    )

    if historical_df.empty:
        print("Cannot run backtest, no historical data.")
        return

    # --- Simulation Setup ---
    initial_capital = Config.INITIAL_CAPITAL
    cash = initial_capital
    portfolio_value = initial_capital
    quantity = 0
    buy_price = 0
    daily_values = []

    print(f"Backtesting on {len(historical_df)} data points for {stock_symbol}...")

    # Iterate through each data point in the historical data
    for i in range(1, len(historical_df)):
        current_data_slice = historical_df.iloc[:i]
        signal, reason = strategy.generate_signal(
            current_data_slice
        )  # Sentiment is 0 for backtest

        current_price = historical_df.iloc[i]["close"]

        # --- BUY ---
        if signal == "BUY" and quantity == 0:  # Only buy if we have no position
            capital_to_use = cash * Config.MAX_EXPOSURE_PER_TRADE
            quantity_to_buy = int(capital_to_use / current_price)

            if quantity_to_buy > 0:
                cost = current_price * quantity_to_buy
                taxes = tax_calculator.calculate_taxes(cost, "BUY")
                total_cost = cost + taxes

                if cash >= total_cost:
                    cash -= total_cost
                    quantity = quantity_to_buy
                    buy_price = current_price
                    print(
                        f"{historical_df.index[i].date()}: BUY {quantity} @ {current_price:.2f} | Reason: {reason}"
                    )

        # --- SELL ---
        elif signal == "SELL" and quantity > 0:  # Only sell if we have a position
            revenue = current_price * quantity
            taxes = tax_calculator.calculate_taxes(revenue, "SELL")
            total_revenue = revenue - taxes

            cash += total_revenue
            pnl = (current_price - buy_price) * quantity - taxes
            print(
                f"{historical_df.index[i].date()}: SELL {quantity} @ {current_price:.2f} | PnL: {pnl:.2f} | Reason: {reason}"
            )
            quantity = 0
            buy_price = 0

        # Update portfolio value for the day
        current_portfolio_value = cash + (quantity * current_price)
        daily_values.append(current_portfolio_value)

    # --- Performance Metrics ---
    returns = (
        pd.Series(daily_values, index=historical_df.index[1:]).pct_change().dropna()
    )

    final_portfolio_value = daily_values[-1]
    total_pnl = final_portfolio_value - initial_capital
    total_pnl_percent = (total_pnl / initial_capital) * 100

    sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)  # Annualized Sharpe

    cumulative_returns = (1 + returns).cumprod()
    peak = cumulative_returns.expanding(min_periods=1).max()
    drawdown = cumulative_returns / peak - 1
    max_drawdown = drawdown.min()

    calmar_ratio = (
        (returns.mean() * 252) / abs(max_drawdown) if max_drawdown != 0 else 0
    )

    print("\n--- Backtest Results ---")
    print(f"Initial Capital:       ₹{initial_capital:,.2f}")
    print(f"Final Portfolio Value:   ₹{final_portfolio_value:,.2f}")
    print(f"Total Profit/Loss:       ₹{total_pnl:,.2f} ({total_pnl_percent:.2f}%)")
    print("---")
    print(f"Annualized Sharpe Ratio: {sharpe_ratio:.2f}")
    print(f"Max Drawdown:            {max_drawdown:.2%}")
    print(f"Calmar Ratio:            {calmar_ratio:.2f}")
    print("------------------------\n")
