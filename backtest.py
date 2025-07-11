# backtest.py
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

    # Backtest on entire universe with configurable params to avoid API limits
    stock_universe = Config.STOCKS
    historical_data = data_handler.get_historical_data(
        stock_universe,
        days=Config.BACKTEST_DAYS,
        interval_minutes=Config.BACKTEST_INTERVAL_MINUTES
    )

    if not historical_data:
        print("Cannot run backtest, no historical data fetched.")
        return

    # Fetch Nifty data separately for regime analysis (use correct Groww symbol for Nifty 50)
    nifty_data = data_handler.get_historical_data(
        "NIFTY",  # Corrected symbol for Nifty 50 in Groww API
        days=Config.BACKTEST_DAYS,
        interval_minutes=Config.BACKTEST_INTERVAL_MINUTES
    )

    # --- Simulation Setup ---
    initial_capital = Config.INITIAL_CAPITAL
    cash = initial_capital
    positions = {stock: 0 for stock in stock_universe}
    buy_prices = {stock: 0 for stock in stock_universe}
    daily_values = []

    print(f"Backtesting on {len(stock_universe)} stocks...")

    # Assume combined DataFrame for simplicity (handle missing stocks gracefully)
    combined_df = pd.concat({s: df for s, df in historical_data.items() if not df.empty}, axis=1)

    # Determine the minimum length to avoid index mismatches
    if combined_df.empty:
        print("No valid data for backtesting.")
        return
    min_length = len(combined_df)

    for i in range(1, min_length):
        current_slice = combined_df.iloc[:i]
        current_nifty_slice = nifty_data.iloc[:i] if not nifty_data.empty else pd.DataFrame()

        # Generate signals for portfolio
        signals = strategy.generate_signal(
            data=current_nifty_slice,
            full_stock_data=current_slice
        )

        if isinstance(signals, list):
            for stock, signal, reason in signals:
                if stock not in stock_universe or stock not in historical_data or historical_data[stock].empty:
                    continue
                current_price = current_slice[(stock, "close")].iloc[-1] if (stock, "close") in current_slice.columns else np.nan
                if np.isnan(current_price):
                    continue

                if signal == "BUY" and positions[stock] == 0:
                    capital_to_use = min(cash * Config.MAX_EXPOSURE_PER_TRADE, cash * Config.RISK_PER_TRADE)
                    quantity = int(capital_to_use / current_price)
                    if quantity > 0:
                        cost = current_price * quantity * 1.001  # Simulate slippage
                        taxes = tax_calculator.calculate_taxes(cost, "BUY")
                        total_cost = cost + taxes
                        if cash >= total_cost:
                            cash -= total_cost
                            positions[stock] = quantity
                            buy_prices[stock] = current_price
                            print(f"BUY {quantity} {stock} @ {current_price:.2f} | Reason: {reason}")

                elif signal == "SELL" and positions[stock] > 0:
                    revenue = current_price * positions[stock] * 0.999  # Slippage
                    taxes = tax_calculator.calculate_taxes(revenue, "SELL")
                    total_revenue = revenue - taxes
                    cash += total_revenue
                    pnl = (current_price - buy_prices[stock]) * positions[stock] - taxes
                    print(f"SELL {positions[stock]} {stock} @ {current_price:.2f} | PnL: {pnl:.2f} | Reason: {reason}")
                    positions[stock] = 0

        # Update portfolio value
        portfolio_value = cash + sum(
            positions[s] * combined_df[(s, "close")].iloc[i]
            if (s, "close") in combined_df.columns and i < len(combined_df[(s, "close")]) else 0
            for s in stock_universe
        )
        daily_values.append(portfolio_value)

    # --- Performance Metrics ---
    returns = pd.Series(daily_values).pct_change().dropna()
    final_portfolio_value = daily_values[-1] if daily_values else initial_capital
    total_pnl = final_portfolio_value - initial_capital
    total_pnl_percent = (total_pnl / initial_capital) * 100 if initial_capital > 0 else 0

    sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() != 0 else 0

    cumulative_returns = (1 + returns).cumprod()
    peak = cumulative_returns.expanding(min_periods=1).max()
    drawdown = cumulative_returns / peak - 1
    max_drawdown = drawdown.min()

    calmar_ratio = (returns.mean() * 252) / abs(max_drawdown) if max_drawdown != 0 else 0

    print("\n--- Backtest Results ---")
    print(f"Initial Capital:       ₹{initial_capital:,.2f}")
    print(f"Final Portfolio Value:   ₹{final_portfolio_value:,.2f}")
    print(f"Total Profit/Loss:       ₹{total_pnl:,.2f} ({total_pnl_percent:.2f}%)")
    print("---")
    print(f"Annualized Sharpe Ratio: {sharpe_ratio:.2f}")
    print(f"Max Drawdown:            {max_drawdown:.2%}")
    print(f"Calmar Ratio:            {calmar_ratio:.2f}")
    print("------------------------\n")
