# backtest.py
import pandas as pd
import numpy as np
import ta

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
    stock_universe = [s for s in Config.STOCKS]  # Copy to modify
    historical_data = data_handler.get_historical_data(
        stock_universe,
        days=Config.BACKTEST_DAYS,
        interval_minutes=Config.BACKTEST_INTERVAL_MINUTES
    )

    # Update universe to only include successfully fetched stocks
    stock_universe = list(historical_data.keys())
    if not stock_universe:
        print("Cannot run backtest, no historical data fetched for any stock.")
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
    peak_prices = {stock: 0 for stock in stock_universe}  # For trailing stop
    daily_values = []
    trailing_stop_pct = Config.STOP_LOSS_PCT
    take_profit_pct = Config.TAKE_PROFIT_PCT
    trades = []  # List to track trades for metrics (e.g., [{'stock': 'ABC', 'entry_price': 100, 'exit_price': 110, 'pnl': 10, 'type': 'win'}])

    print(f"Backtesting on {len(stock_universe)} stocks (fetched successfully)...")

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
        print(f"Signals at step {i}: {signals}")  # Debug logging for signals

        # Handle list of signals
        if isinstance(signals, list):
            for signal_tuple in signals:
                if len(signal_tuple) != 3:
                    continue
                stock, signal, reason = signal_tuple
                if stock not in stock_universe or stock not in historical_data or historical_data[stock].empty:
                    continue
                current_price = current_slice[(stock, "close")].iloc[-1] if (stock, "close") in current_slice.columns else np.nan
                if np.isnan(current_price):
                    continue

                # Dynamic position sizing based on ATR (risk control) - handle NaN ATR
                try:
                    atr = ta.volatility.AverageTrueRange(high=current_slice[(stock, "high")], low=current_slice[(stock, "low")], close=current_slice[(stock, "close")]).average_true_range().iloc[-1]
                    if np.isnan(atr):
                        atr = current_price * 0.01  # Default to 1% of price if ATR NaN
                except:
                    atr = current_price * 0.01  # Fallback
                position_size = int((cash * Config.RISK_PER_TRADE) / atr)  # Size based on volatility

                if signal == "BUY" and positions[stock] == 0:
                    capital_to_use = min(cash * Config.MAX_EXPOSURE_PER_TRADE, cash * Config.RISK_PER_TRADE)
                    quantity = min(position_size, int(capital_to_use / current_price))
                    if quantity > 0:
                        cost = current_price * quantity * 1.001  # Simulate slippage
                        taxes = tax_calculator.calculate_taxes(cost, "BUY")
                        total_cost = cost + taxes
                        if cash >= total_cost:
                            cash -= total_cost
                            positions[stock] = quantity
                            buy_prices[stock] = current_price
                            peak_prices[stock] = current_price  # Init peak for trailing
                            print(f"BUY {quantity} {stock} @ {current_price:.2f} | Reason: {reason}")
                            trades.append({'stock': stock, 'entry_price': current_price, 'quantity': quantity, 'entry_step': i, 'taxes': taxes})

                elif signal == "SELL" and positions[stock] > 0:
                    revenue = current_price * positions[stock] * 0.999  # Slippage
                    taxes = tax_calculator.calculate_taxes(revenue, "SELL")
                    total_revenue = revenue - taxes
                    cash += total_revenue
                    pnl = (current_price - buy_prices[stock]) * positions[stock] - taxes
                    print(f"SELL {positions[stock]} {stock} @ {current_price:.2f} | PnL: {pnl:.2f} | Reason: {reason}")
                    # Record trade
                    trade_type = 'win' if pnl > 0 else 'loss'
                    trades.append({'stock': stock, 'exit_price': current_price, 'pnl': pnl, 'type': trade_type, 'exit_step': i, 'taxes': taxes})
                    positions[stock] = 0

        # Handle single tuple signals (e.g., from pairs)
        elif isinstance(signals, tuple):
            instrument, signal, reason = signals
            if signal in ["BUY_SPREAD", "SELL_SPREAD", "EXIT_SPREAD"]:
                # Simulate spread trade (long one, short one - assuming no actual shorting, just log for now)
                stock1, stock2 = instrument.split(',')
                if stock1 not in stock_universe or stock2 not in stock_universe:
                    continue
                price1 = current_slice[(stock1, "close")].iloc[-1] if (stock1, "close") in current_slice.columns else np.nan
                price2 = current_slice[(stock2, "close")].iloc[-1] if (stock2, "close") in current_slice.columns else np.nan
                if np.isnan(price1) or np.isnan(price2):
                    continue
                capital_to_use = min(cash * Config.MAX_EXPOSURE_PER_TRADE, cash * Config.RISK_PER_TRADE)
                qty1 = int(capital_to_use / price1)
                qty2 = int(capital_to_use / price2)
                if qty1 > 0 and qty2 > 0:
                    if signal == "BUY_SPREAD":
                        # Long stock1, Short stock2
                        cost = price1 * qty1 * 1.001
                        revenue = price2 * qty2 * 0.999  # Simulated short sell
                        taxes = tax_calculator.calculate_taxes(cost, "BUY") + tax_calculator.calculate_taxes(revenue, "SELL")
                        net = revenue - cost - taxes
                        cash += net
                        print(f"BUY_SPREAD: Long {qty1} {stock1} @ {price1:.2f}, Short {qty2} {stock2} @ {price2:.2f} | Net: {net:.2f} | Reason: {reason}")
                        trades.append({'stock': f"{stock1}-{stock2}", 'entry_price': (price1, price2), 'quantity': (qty1, qty2), 'entry_step': i, 'taxes': taxes})
                    elif signal == "SELL_SPREAD":
                        # Short stock1, Long stock2
                        revenue = price1 * qty1 * 0.999  # Simulated short sell
                        cost = price2 * qty2 * 1.001
                        taxes = tax_calculator.calculate_taxes(revenue, "SELL") + tax_calculator.calculate_taxes(cost, "BUY")
                        net = revenue - cost - taxes
                        cash += net
                        print(f"SELL_SPREAD: Short {qty1} {stock1} @ {price1:.2f}, Long {qty2} {stock2} @ {price2:.2f} | Net: {net:.2f} | Reason: {reason}")
                        trades.append({'stock': f"{stock1}-{stock2}", 'entry_price': (price1, price2), 'quantity': (qty1, qty2), 'entry_step': i, 'taxes': taxes})
                    elif signal == "EXIT_SPREAD":
                        # Simulate closing spread (assume flat for simplicity)
                        print(f"EXIT_SPREAD: Closing {instrument} | Reason: {reason}")
            else:
                stock = instrument
                if stock not in stock_universe or stock not in historical_data or historical_data[stock].empty:
                    continue
                current_price = current_slice[(stock, "close")].iloc[-1] if (stock, "close") in current_slice.columns else np.nan
                if np.isnan(current_price):
                    continue

                # Dynamic position sizing based on ATR (risk control) - handle NaN ATR
                try:
                    atr = ta.volatility.AverageTrueRange(high=current_slice[(stock, "high")], low=current_slice[(stock, "low")], close=current_slice[(stock, "close")]).average_true_range().iloc[-1]
                    if np.isnan(atr):
                        atr = current_price * 0.01  # Default to 1% of price if ATR NaN
                except:
                    atr = current_price * 0.01  # Fallback
                position_size = int((cash * Config.RISK_PER_TRADE) / atr)  # Size based on volatility

                if signal == "BUY" and positions[stock] == 0:
                    capital_to_use = min(cash * Config.MAX_EXPOSURE_PER_TRADE, cash * Config.RISK_PER_TRADE)
                    quantity = min(position_size, int(capital_to_use / current_price))
                    if quantity > 0:
                        cost = current_price * quantity * 1.001  # Simulate slippage
                        taxes = tax_calculator.calculate_taxes(cost, "BUY")
                        total_cost = cost + taxes
                        if cash >= total_cost:
                            cash -= total_cost
                            positions[stock] = quantity
                            buy_prices[stock] = current_price
                            peak_prices[stock] = current_price  # Init peak for trailing
                            print(f"BUY {quantity} {stock} @ {current_price:.2f} | Reason: {reason}")
                            trades.append({'stock': stock, 'entry_price': current_price, 'quantity': quantity, 'entry_step': i, 'taxes': taxes})

                elif signal == "SELL" and positions[stock] > 0:
                    revenue = current_price * positions[stock] * 0.999  # Slippage
                    taxes = tax_calculator.calculate_taxes(revenue, "SELL")
                    total_revenue = revenue - taxes
                    cash += total_revenue
                    pnl = (current_price - buy_prices[stock]) * positions[stock] - taxes
                    print(f"SELL {positions[stock]} {stock} @ {current_price:.2f} | PnL: {pnl:.2f} | Reason: {reason}")
                    # Record trade
                    trade_type = 'win' if pnl > 0 else 'loss'
                    trades.append({'stock': stock, 'exit_price': current_price, 'pnl': pnl, 'type': trade_type, 'exit_step': i, 'taxes': taxes})
                    positions[stock] = 0

        # Apply trailing stop and take-profit for open positions
        for stock in list(positions.keys()):
            if positions[stock] > 0:
                current_price = current_slice[(stock, "close")].iloc[-1] if (stock, "close") in current_slice.columns else np.nan
                if np.isnan(current_price):
                    continue
                # Update peak for trailing
                peak_prices[stock] = max(peak_prices[stock], current_price)
                # Trailing stop
                if current_price < peak_prices[stock] * (1 - trailing_stop_pct):
                    revenue = current_price * positions[stock] * 0.999
                    taxes = tax_calculator.calculate_taxes(revenue, "SELL")
                    total_revenue = revenue - taxes
                    cash += total_revenue
                    pnl = (current_price - buy_prices[stock]) * positions[stock] - taxes
                    print(f"TRAILING STOP SELL {positions[stock]} {stock} @ {current_price:.2f} | PnL: {pnl:.2f}")
                    # Record trade
                    trade_type = 'win' if pnl > 0 else 'loss'
                    trades.append({'stock': stock, 'exit_price': current_price, 'pnl': pnl, 'type': trade_type, 'exit_step': i, 'taxes': taxes})
                    positions[stock] = 0
                # Take-profit
                elif current_price > buy_prices[stock] * (1 + take_profit_pct):
                    revenue = current_price * positions[stock] * 0.999
                    taxes = tax_calculator.calculate_taxes(revenue, "SELL")
                    total_revenue = revenue - taxes
                    cash += total_revenue
                    pnl = (current_price - buy_prices[stock]) * positions[stock] - taxes
                    print(f"TAKE PROFIT SELL {positions[stock]} {stock} @ {current_price:.2f} | PnL: {pnl:.2f}")
                    # Record trade
                    trade_type = 'win' if pnl > 0 else 'loss'
                    trades.append({'stock': stock, 'exit_price': current_price, 'pnl': pnl, 'type': trade_type, 'exit_step': i, 'taxes': taxes})
                    positions[stock] = 0

        # Update portfolio value (with compounding - cash is reinvested)
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

    # Additional Metrics
    num_trades = len(trades)
    if num_trades > 0:
        wins = sum(1 for t in trades if 'pnl' in t and t['pnl'] > 0)
        losses = sum(1 for t in trades if 'pnl' in t and t['pnl'] <= 0)
        win_rate = (wins / num_trades) * 100 if num_trades > 0 else 0
        avg_pnl = sum(t['pnl'] for t in trades if 'pnl' in t) / num_trades
        avg_win = sum(t['pnl'] for t in trades if 'pnl' in t and t['pnl'] > 0) / wins if wins > 0 else 0
        avg_loss = sum(t['pnl'] for t in trades if 'pnl' in t and t['pnl'] <= 0) / losses if losses > 0 else 0
        expectancy = (win_rate / 100 * avg_win) - ((1 - win_rate / 100) * abs(avg_loss))
        profit_factor = abs(sum(t['pnl'] for t in trades if 'pnl' in t and t['pnl'] > 0) / sum(abs(t['pnl']) for t in trades if 'pnl' in t and t['pnl'] <= 0)) if losses > 0 else np.inf
        total_taxes = sum(t.get('taxes', 0) for t in trades)  # Assume taxes tracked in trades if needed
    else:
        win_rate = 0
        avg_pnl = 0
        avg_win = 0
        avg_loss = 0
        expectancy = 0
        profit_factor = 0
        total_taxes = 0

    print("\n--- Backtest Results ---")
    print(f"Initial Capital:       ₹{initial_capital:,.2f}")
    print(f"Final Portfolio Value:   ₹{final_portfolio_value:,.2f}")
    print(f"Total Profit/Loss:       ₹{total_pnl:,.2f} ({total_pnl_percent:.2f}%)")
    print(f"Number of Trades:        {num_trades}")
    print(f"Win Rate:                {win_rate:.2f}%")
    print(f"Average PnL per Trade:   ₹{avg_pnl:.2f}")
    print(f"Average Win:             ₹{avg_win:.2f}")
    print(f"Average Loss:            ₹{avg_loss:.2f}")
    print(f"Expectancy:              ₹{expectancy:.2f}")
    print(f"Profit Factor:           {profit_factor:.2f}")
    print(f"Total Taxes/Fees:        ₹{total_taxes:.2f}")
    print("---")
    print(f"Annualized Sharpe Ratio: {sharpe_ratio:.2f}")
    print(f"Max Drawdown:            {max_drawdown:.2%}")
    print(f"Calmar Ratio:            {calmar_ratio:.2f}")
    print("------------------------\n")