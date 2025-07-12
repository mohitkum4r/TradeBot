from datetime import datetime, timedelta  # For settlement dates

import pandas as pd
import numpy as np
import json
import csv

import ta

from autotrade.strategies.base_strategy import BaseStrategy
from autotrade.services.data_handler import DataHandler
from autotrade.config import Config
from autotrade.services import tax_calculator
# For LLM review
import ollama
# For ML training
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import LabelEncoder  # For encoding signals
from joblib import dump, load  # To save/load model
from typing import Dict, List


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
    # NEW: Pending cash for T+1 settlements (list of {'amount': float, 'release_step': int})
    pending_cash = []
    positions = {stock: 0 for stock in stock_universe}
    buy_prices = {stock: 0 for stock in stock_universe}
    peak_prices = {stock: 0 for stock in stock_universe}  # For trailing stop
    daily_values = []
    trailing_stop_pct = Config.STOP_LOSS_PCT
    take_profit_pct = Config.TAKE_PROFIT_PCT
    trades = []  # List to track trades for metrics (e.g., [{'stock': 'ABC', 'entry_price': 100, 'exit_price': 110, 'pnl': 10, 'type': 'win'}])
    # NEW: Detailed logs for all data (signals, features, regimes) for examiner and LLM
    detailed_logs = []  # List of dicts: {'step': i, 'regime': str, 'signals': list/tuple, 'features': dict, 'positions': dict, 'cash': float, 'market_snapshot': dict of DFs, 'optimal_signal': dict}  # Added optimal for ML

    print(f"Backtesting on {len(stock_universe)} stocks...")

    # Assume combined DataFrame for simplicity (handle missing stocks gracefully)
    combined_df = pd.concat({s: df for s, df in historical_data.items() if not df.empty}, axis=1)

    # Determine the minimum length to avoid index mismatches
    if combined_df.empty:
        print("No valid data for backtesting.")
        return
    min_length = len(combined_df)

    # NEW: Steps per "day" for settlement (e.g., 390 for 1-min in 6.5hr day; adjust based on interval)
    steps_per_day = int(
        390 / Config.BACKTEST_INTERVAL_MINUTES) if Config.BACKTEST_INTERVAL_MINUTES > 0 else 1  # Avoid division by zero

    # NEW: Cumulative ideal PnL tracker (updated per step)
    cumulative_ideal_pnl = 0.0

    for i in range(1, min_length):
        current_slice = combined_df.iloc[:i]
        current_nifty_slice = nifty_data.iloc[:i] if not nifty_data.empty else pd.DataFrame()

        # NEW: Release pending cash (T+1 simulation)
        pending_to_release = [p for p in pending_cash if p['release_step'] <= i]
        for p in pending_to_release:
            cash += p['amount']
            pending_cash.remove(p)
            print(f"Released pending cash ₹{p['amount']:.2f} at step {i} (T+1 settlement)")

        # Generate signals for portfolio
        signals = strategy.generate_signal(
            data=current_nifty_slice,
            full_stock_data=current_slice
        )
        print(f"Signals at step {i}: {signals}")  # Debug logging for signals

        # NEW: Compute features for logging (e.g., ADX, ATR, RSI for each stock) with handling for short data
        features = {}
        for stock in stock_universe:
            if (stock, 'close') in current_slice.columns:
                stock_data = current_slice[stock]
                stock_features = {'adx': None, 'atr': None, 'rsi': None}
                if len(stock_data) >= 14:  # Min for indicators
                    try:
                        adx = ta.trend.ADXIndicator(stock_data['high'], stock_data['low'], stock_data['close'],
                                                    window=14).adx().iloc[-1]
                        stock_features['adx'] = adx if not pd.isna(adx) else None
                    except (IndexError, ValueError) as e:
                        print(f"ADX failed for {stock} at step {i}: {e}. Setting to None.")

                    try:
                        atr = ta.volatility.AverageTrueRange(stock_data['high'], stock_data['low'], stock_data['close'],
                                                             window=14).average_true_range().iloc[-1]
                        stock_features['atr'] = atr if not pd.isna(atr) else None
                    except (IndexError, ValueError) as e:
                        print(f"ATR failed for {stock} at step {i}: {e}. Setting to None.")

                    try:
                        rsi = ta.momentum.RSIIndicator(stock_data['close'], window=14).rsi().iloc[-1]
                        stock_features['rsi'] = rsi if not pd.isna(rsi) else None
                    except (IndexError, ValueError) as e:
                        print(f"RSI failed for {stock} at step {i}: {e}. Setting to None.")
                features[stock] = stock_features
            else:
                features[stock] = {'adx': None, 'atr': None, 'rsi': None}

        # NEW: Compute optimal signals per stock for ML learning (using future data - cheating for training only)
        optimal_signals = {}
        for stock in stock_universe:
            if (stock, 'close') in combined_df.columns:
                full_stock_data = combined_df[stock]  # Full future data for this stock
                if i < len(full_stock_data) - 1:  # Need next point for prediction
                    current_close = full_stock_data['close'].iloc[i - 1]  # Current at step i
                    next_close = full_stock_data['close'].iloc[i]  # "Future" next step
                    price_change_pct = (next_close - current_close) / current_close
                    if price_change_pct > 0.01:  # Arbitrary threshold for BUY (1% rise)
                        optimal_signals[stock] = 'BUY'
                    elif price_change_pct < -0.01:  # 1% drop for SELL
                        optimal_signals[stock] = 'SELL'
                    else:
                        optimal_signals[stock] = 'HOLD'
                else:
                    optimal_signals[stock] = 'HOLD'  # No future data
            else:
                optimal_signals[stock] = 'HOLD'

        # NEW: Log everything, even HOLD signals, with optimal for ML
        step_log = {
            'step': i,
            'regime': 'Unknown',  # Update based on ADX (set in regime logic below)
            'signals': signals,  # All signals, including HOLD
            'features': features,  # Computed indicators per stock
            'optimal_signals': optimal_signals,  # NEW: For ML training
            'positions': positions.copy(),
            'cash': cash,
            'market_snapshot': {stock: current_slice[stock].iloc[-1].to_dict() for stock in stock_universe if
                                (stock, 'close') in current_slice.columns}  # Latest OHLCV per stock
        }
        detailed_logs.append(step_log)

        # NEW: Update cumulative ideal PnL per step (buy at slice min, sell at slice max for each stock, with costs)
        step_ideal_pnl = 0.0
        for stock in stock_universe:
            if (stock, 'close') in current_slice.columns:
                stock_slice = current_slice[stock]
                if len(stock_slice) >= 2:  # Need at least 2 points for min/max
                    min_price = stock_slice['low'].min()
                    max_price = stock_slice['high'].max()
                    if not pd.isna(min_price) and not pd.isna(max_price) and min_price < max_price:
                        qty = int(initial_capital * Config.MAX_EXPOSURE_PER_TRADE / min_price)
                        # Include slippage and taxes for realism
                        buy_cost = min_price * qty * 1.001
                        sell_revenue = max_price * qty * 0.999
                        taxes = tax_calculator.calculate_taxes(buy_cost, "BUY") + tax_calculator.calculate_taxes(
                            sell_revenue, "SELL")
                        ideal_profit = sell_revenue - buy_cost - taxes
                        step_ideal_pnl += ideal_profit
        cumulative_ideal_pnl += step_ideal_pnl  # Cumulative over all steps

        # Handle list of signals
        if isinstance(signals, list):
            for signal_tuple in signals:
                if len(signal_tuple) != 3:
                    continue
                stock, signal, reason = signal_tuple
                if stock not in stock_universe or stock not in historical_data or historical_data[stock].empty:
                    continue
                current_price = current_slice[(stock, "close")].iloc[-1] if (stock,
                                                                             "close") in current_slice.columns else np.nan
                if np.isnan(current_price):
                    continue

                # Dynamic position sizing based on ATR (risk control) - handle NaN ATR
                try:
                    atr = ta.volatility.AverageTrueRange(high=current_slice[(stock, "high")],
                                                         low=current_slice[(stock, "low")], close=current_slice[
                            (stock, "close")]).average_true_range().iloc[-1]
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
                            trades.append(
                                {'stock': stock, 'entry_price': current_price, 'quantity': quantity, 'entry_step': i,
                                 'taxes': taxes})
                            print("Cha-ching! Position opened—let's make some money! 💰")  # Motivational log

                elif signal == "SELL" and positions[stock] > 0:
                    revenue = current_price * positions[stock] * 0.999  # Slippage
                    taxes = tax_calculator.calculate_taxes(revenue, "SELL")
                    total_revenue = revenue - taxes
                    # NEW: Add to pending_cash for T+1 settlement (not immediate cash)
                    release_step = i + steps_per_day  # Release next "day"
                    pending_cash.append({'amount': total_revenue, 'release_step': release_step})
                    print(f"SELL added to pending settlement: ₹{total_revenue:.2f} available at step {release_step}")
                    pnl = (current_price - buy_prices[stock]) * positions[stock] - taxes
                    print(f"SELL {positions[stock]} {stock} @ {current_price:.2f} | PnL: {pnl:.2f} | Reason: {reason}")
                    # Record trade
                    trade_type = 'win' if pnl > 0 else 'loss'
                    trades.append(
                        {'stock': stock, 'exit_price': current_price, 'pnl': pnl, 'type': trade_type, 'exit_step': i,
                         'taxes': taxes})
                    positions[stock] = 0
                    if pnl > 0:
                        print(f"Cha-ching! Profit of ₹{pnl:.2f} banked—money in the pocket! 💸")
                    else:
                        print(f"Oops, loss of ₹{pnl:.2f}—let's learn and get back stronger! 📈")

        # Handle single tuple signals (e.g., from pairs)
        elif isinstance(signals, tuple):
            instrument, signal, reason = signals
            if signal in ["BUY_SPREAD", "SELL_SPREAD", "EXIT_SPREAD"]:
                # Simulate spread trade (long one, short one - assuming no actual shorting, just log for now)
                stock1, stock2 = instrument.split(',')
                if stock1 not in stock_universe or stock2 not in stock_universe:
                    continue
                price1 = current_slice[(stock1, "close")].iloc[-1] if (stock1,
                                                                       "close") in current_slice.columns else np.nan
                price2 = current_slice[(stock2, "close")].iloc[-1] if (stock2,
                                                                       "close") in current_slice.columns else np.nan
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
                        taxes = tax_calculator.calculate_taxes(cost, "BUY") + tax_calculator.calculate_taxes(revenue,
                                                                                                             "SELL")
                        net = revenue - cost - taxes
                        cash += net
                        print(
                            f"BUY_SPREAD: Long {qty1} {stock1} @ {price1:.2f}, Short {qty2} {stock2} @ {price2:.2f} | Net: {net:.2f} | Reason: {reason}")
                        trades.append(
                            {'stock': f"{stock1}-{stock2}", 'entry_price': (price1, price2), 'quantity': (qty1, qty2),
                             'entry_step': i, 'taxes': taxes})
                        if net > 0:
                            print(f"Cha-ching! Spread profit of ₹{net:.2f}—arbitrage magic! 💰")
                    elif signal == "SELL_SPREAD":
                        # Short stock1, Long stock2
                        revenue = price1 * qty1 * 0.999  # Simulated short sell
                        cost = price2 * qty2 * 1.001
                        taxes = tax_calculator.calculate_taxes(revenue, "SELL") + tax_calculator.calculate_taxes(cost,
                                                                                                                 "BUY")
                        net = revenue - cost - taxes
                        cash += net
                        print(
                            f"SELL_SPREAD: Short {qty1} {stock1} @ {price1:.2f}, Long {qty2} {stock2} @ {price2:.2f} | Net: {net:.2f} | Reason: {reason}")
                        trades.append(
                            {'stock': f"{stock1}-{stock2}", 'entry_price': (price1, price2), 'quantity': (qty1, qty2),
                             'entry_step': i, 'taxes': taxes})
                        if net > 0:
                            print(f"Cha-ching! Spread profit of ₹{net:.2f}—arbitrage magic! 💰")
                    elif signal == "EXIT_SPREAD":
                        # Simulate closing spread (assume flat for simplicity)
                        print(f"EXIT_SPREAD: Closing {instrument} | Reason: {reason}")
            else:
                stock = instrument
                if stock not in stock_universe or stock not in historical_data or historical_data[stock].empty:
                    continue
                current_price = current_slice[(stock, "close")].iloc[-1] if (stock,
                                                                             "close") in current_slice.columns else np.nan
                if np.isnan(current_price):
                    continue

                # Dynamic position sizing based on ATR (risk control) - handle NaN ATR
                try:
                    atr = ta.volatility.AverageTrueRange(high=current_slice[(stock, "high")],
                                                         low=current_slice[(stock, "low")], close=current_slice[
                            (stock, "close")]).average_true_range().iloc[-1]
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
                            trades.append(
                                {'stock': stock, 'entry_price': current_price, 'quantity': quantity, 'entry_step': i,
                                 'taxes': taxes})
                            print("Cha-ching! Position opened—let's make some money! 💰")

                elif signal == "SELL" and positions[stock] > 0:
                    revenue = current_price * positions[stock] * 0.999  # Slippage
                    taxes = tax_calculator.calculate_taxes(revenue, "SELL")
                    total_revenue = revenue - taxes
                    # NEW: Add to pending_cash for T+1 settlement (not immediate cash)
                    release_step = i + steps_per_day  # Release next "day"
                    pending_cash.append({'amount': total_revenue, 'release_step': release_step})
                    print(f"SELL added to pending settlement: ₹{total_revenue:.2f} available at step {release_step}")
                    pnl = (current_price - buy_prices[stock]) * positions[stock] - taxes
                    print(f"SELL {positions[stock]} {stock} @ {current_price:.2f} | PnL: {pnl:.2f} | Reason: {reason}")
                    # Record trade
                    trade_type = 'win' if pnl > 0 else 'loss'
                    trades.append(
                        {'stock': stock, 'exit_price': current_price, 'pnl': pnl, 'type': trade_type, 'exit_step': i,
                         'taxes': taxes})
                    positions[stock] = 0
                    if pnl > 0:
                        print(f"Cha-ching! Profit of ₹{pnl:.2f} banked—money in the pocket! 💸")
                    else:
                        print(f"Oops, loss of ₹{pnl:.2f}—let's learn and get back stronger! 📈")

        # Apply trailing stop and take-profit for open positions
        for stock in list(positions.keys()):
            if positions[stock] > 0:
                current_price = current_slice[(stock, "close")].iloc[-1] if (stock,
                                                                             "close") in current_slice.columns else np.nan
                if np.isnan(current_price):
                    continue
                # Update peak for trailing
                peak_prices[stock] = max(peak_prices[stock], current_price)
                # Trailing stop
                if current_price < peak_prices[stock] * (1 - trailing_stop_pct):
                    revenue = current_price * positions[stock] * 0.999
                    taxes = tax_calculator.calculate_taxes(revenue, "SELL")
                    total_revenue = revenue - taxes
                    # NEW: Pending for T+1
                    release_step = i + steps_per_day
                    pending_cash.append({'amount': total_revenue, 'release_step': release_step})
                    print(f"TRAILING STOP SELL added to pending: ₹{total_revenue:.2f} at step {release_step}")
                    pnl = (current_price - buy_prices[stock]) * positions[stock] - taxes
                    print(f"TRAILING STOP SELL {positions[stock]} {stock} @ {current_price:.2f} | PnL: {pnl:.2f}")
                    # Record trade
                    trade_type = 'win' if pnl > 0 else 'loss'
                    trades.append(
                        {'stock': stock, 'exit_price': current_price, 'pnl': pnl, 'type': trade_type, 'exit_step': i,
                         'taxes': taxes})
                    positions[stock] = 0
                    if pnl > 0:
                        print(f"Cha-ching! Profit of ₹{pnl:.2f} from trailing stop! 💰")
                # Take-profit
                elif current_price > buy_prices[stock] * (1 + take_profit_pct):
                    revenue = current_price * positions[stock] * 0.999
                    taxes = tax_calculator.calculate_taxes(revenue, "SELL")
                    total_revenue = revenue - taxes
                    # NEW: Pending for T+1
                    release_step = i + steps_per_day
                    pending_cash.append({'amount': total_revenue, 'release_step': release_step})
                    print(f"TAKE PROFIT SELL added to pending: ₹{total_revenue:.2f} at step {release_step}")
                    pnl = (current_price - buy_prices[stock]) * positions[stock] - taxes
                    print(f"TAKE PROFIT SELL {positions[stock]} {stock} @ {current_price:.2f} | PnL: {pnl:.2f}")
                    # Record trade
                    trade_type = 'win' if pnl > 0 else 'loss'
                    trades.append(
                        {'stock': stock, 'exit_price': current_price, 'pnl': pnl, 'type': trade_type, 'exit_step': i,
                         'taxes': taxes})
                    positions[stock] = 0
                    print(f"Cha-ching! Locked in profit of ₹{pnl:.2f}—smart trading pays off! 📈")

        # Update portfolio value (with compounding - cash is reinvested)
        portfolio_value = cash + sum(
            positions[s] * combined_df[(s, "close")].iloc[i]
            if (s, "close") in combined_df.columns and i < len(combined_df[(s, "close")]) else 0
            for s in stock_universe
        )
        daily_values.append(portfolio_value)

    # NEW: Release any remaining pending cash at end (for final value)
    for p in pending_cash:
        cash += p['amount']
    final_portfolio_value = cash + sum(
        positions[s] * combined_df[(s, "close")].iloc[-1]
        if (s, "close") in combined_df.columns else 0
        for s in stock_universe
    )

    # --- Performance Metrics ---
    returns = pd.Series(daily_values).pct_change().dropna()
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
        profit_factor = abs(sum(t['pnl'] for t in trades if 'pnl' in t and t['pnl'] > 0) / sum(
            abs(t['pnl']) for t in trades if 'pnl' in t and t['pnl'] <= 0)) if losses > 0 else np.inf
        total_taxes = sum(t.get('taxes', 0) for t in trades)  # Assume taxes tracked in trades if needed
    else:
        win_rate = 0
        avg_pnl = 0
        avg_win = 0
        avg_loss = 0
        expectancy = 0
        profit_factor = 0
        total_taxes = 0

    # NEW: Structured log including detailed_logs
    performance_log = {
        'timestamp': datetime.now().isoformat(),
        'strategy': strategy.__class__.__name__,
        'initial_capital': initial_capital,
        'final_value': final_portfolio_value,
        'total_pnl': total_pnl,
        'pnl_percent': total_pnl_percent,
        'num_trades': num_trades,
        'win_rate': win_rate,
        'avg_pnl': avg_pnl,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'expectancy': expectancy,
        'profit_factor': profit_factor,
        'total_taxes': total_taxes,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'calmar_ratio': calmar_ratio,
        'trades': trades,  # Full trade details
        'detailed_logs': detailed_logs  # All steps' data for examiner/LLM
    }

    # Save to JSON for LLM/analysis
    with open('backtest_logs.json', 'a') as f:  # Append for multiple runs
        json.dump(performance_log, f)
        f.write('\n')  # Newline for separation
    print("Backtest log saved to backtest_logs.json for LLM evaluation and optimization.")

    # Save to CSV for easy viewing
    with open('backtest_results.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=performance_log.keys())
        writer.writeheader()
        writer.writerow(performance_log)
    print("Backtest results saved to backtest_results.csv.")

    # NEW: Train ML model on optimal signals from logs
    train_ml_on_optimal(detailed_logs)

    # NEW: Run examiner if enabled
    if Config.EXAMINER_ENABLED:
        examine_backtest(performance_log, historical_data)

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


# NEW: Well-commented ML training function to learn from optimal signals
def train_ml_on_optimal(detailed_logs: List[Dict]) -> None:
    """
    Trains a machine learning model to predict 'optimal' trading signals based on backtest logs.

    Approach:
    1. **Data Extraction:** Loop through detailed_logs to collect features (e.g., ADX, ATR, RSI) and labels ('optimal_signal' per stock/step).
       - Features: Numerical indicators from the log (handle None as 0 for simplicity).
       - Labels: 'BUY', 'SELL', 'HOLD' as computed in backtest (based on next price change >1% threshold).
    2. **Preprocessing:** Flatten into a DataFrame, encode labels (e.g., BUY=0, SELL=1, HOLD=2), handle missing values.
    3. **Training:** Use RandomForestClassifier (good for tabular data, handles non-linearity).
       - Split 80/20 train/test, fit model, evaluate accuracy.
    4. **Output/Save:** Print accuracy, save model as 'optimal_trade_model.joblib' for use in strategies (e.g., predict and filter signals).
    5. **Usage in Live/Strategies:** Load model, input current features, predict signal, e.g., if predict 'BUY' with >70% prob, override rule-based.

    This approximates the 'ideal' path by learning patterns that lead to profitable actions, helping close the PnL gap over time.
    Run after backtests with sufficient logs (>100 steps) for good training.
    """
    print("\n--- Training ML Model on Optimal Signals ---")

    # Step 1: Extract data from logs
    ml_data = []
    for log in detailed_logs:
        step = log['step']
        for stock, feats in log['features'].items():
            optimal = log.get('optimal_signals', {}).get(stock, 'HOLD')
            # Flatten features (add more as needed; handle None)
            row = {
                'step': step,
                'stock': stock,
                'adx': feats['adx'] if feats['adx'] is not None else 0.0,
                'atr': feats['atr'] if feats['atr'] is not None else 0.0,
                'rsi': feats['rsi'] if feats['rsi'] is not None else 50.0,  # Default neutral
                'optimal_signal': optimal
            }
            ml_data.append(row)

    if not ml_data:
        print("No data for ML training (empty logs). Skipping.")
        return

    # Step 2: Preprocess into DataFrame
    df = pd.DataFrame(ml_data)
    # Features (exclude non-numeric like stock/step for now; could one-hot encode stock if needed)
    X = df[['adx', 'atr', 'rsi']]
    y = df['optimal_signal']

    # Encode labels (BUY=0, SELL=1, HOLD=2)
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    # Split data (80% train, 20% test)
    X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)

    # Step 3: Train RandomForestClassifier
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"ML Model Accuracy on Test Set: {accuracy * 100:.2f}%")
    print(f"Class Mapping: {dict(enumerate(le.classes_))}")  # e.g., 0: BUY, 1: HOLD, 2: SELL

    # Step 4: Save model for use in strategies
    dump(model, 'optimal_trade_model.joblib')
    dump(le, 'optimal_label_encoder.joblib')  # Save encoder to decode predictions
    print("Trained model saved as 'optimal_trade_model.joblib'. Load in strategies to predict optimal signals.")


def examine_backtest(performance_log: dict, historical_data: Dict[str, pd.DataFrame]):
    print("\n--- Running Backtest Examiner ---")

    # Step 1: Compute ideal max profit per stock (perfect foresight: buy at min, sell at max)
    ideal_pnl = {}
    ideal_trades = []
    for stock, df in historical_data.items():
        if df.empty:
            continue
        min_price = df['low'].min()
        max_price = df['high'].max()
        if pd.isna(min_price) or pd.isna(max_price):
            continue
        # Assume buy at min, sell at max, with max quantity based on initial capital
        qty = int(performance_log['initial_capital'] * 0.2 / min_price)  # 20% exposure
        ideal_profit = (max_price - min_price) * qty
        ideal_pnl[stock] = ideal_profit
        ideal_trades.append({'stock': stock, 'buy_price': min_price, 'sell_price': max_price, 'qty': qty, 'pnl': ideal_profit})

    total_ideal_pnl = sum(ideal_pnl.values())
    actual_pnl = performance_log['total_pnl']
    pnl_gap = total_ideal_pnl - actual_pnl
    print(f"Ideal Max PnL (Perfect Foresight): ₹{total_ideal_pnl:,.2f}")  # Continued from your line (completed formatting)
    print(f"Actual PnL: ₹{actual_pnl:,.2f}")
    print(f"PnL Gap: ₹{pnl_gap:,.2f} (Opportunity for optimization!)")

    # Step 2: Enhance log with ideal data for LLM
    examiner_log = performance_log.copy()
    examiner_log['ideal_pnl'] = total_ideal_pnl
    examiner_log['pnl_gap'] = pnl_gap
    examiner_log['ideal_trades'] = ideal_trades

    # Step 3: LLM analysis (using Mistral or configured model)
    # FIXED: Access detailed_logs from performance_log, with safe checks
    last_log = performance_log.get('detailed_logs', [])[-1] if performance_log.get('detailed_logs') else {}
    summary = f"""
    Strategy: {performance_log['strategy']}
    Actual PnL: ₹{actual_pnl:,.2f} ({performance_log['pnl_percent']:.2f}%)
    Ideal PnL: ₹{total_ideal_pnl:,.2f}
    PnL Gap: ₹{pnl_gap:,.2f}
    Win Rate: {performance_log['win_rate']:.2f}%
    Num Trades: {performance_log['num_trades']}
    Profit Factor: {performance_log['profit_factor']:.2f}
    Top Trades: {json.dumps(performance_log['trades'][:3], default=str)}  # Sample
    Top Ideal Trades: {json.dumps(ideal_trades[:3], default=str)}  # Sample
    Last Step Log: {json.dumps(last_log, default=str)}  # Last step for context
    """
    prompt = f"""
    You are a trading expert. Analyze this backtest summary and suggest 3 specific, actionable optimizations to close the PnL gap and improve win rate/profit factor.
    Examples: "Lower VOLUME_MULTIPLIER to 1.0 for 20% more trades" or "Add RSI >50 filter to buys in Dual MA strategy".
    Focus on parameter tweaks, new rules, or strategy changes to maximize profits with low risk.
    Do not describe the data structure; only provide the 3 suggestions in bullet points.
    Summary: {summary}
    """
    try:
        response = ollama.generate(model=Config.OLLAMA_MODEL, prompt=prompt)
        suggestions = response['response'].strip()
        print("\n--- LLM (Mistral) Suggestions for Optimization ---")
        print(suggestions)
        # Save suggestions for future use (e.g., auto-apply to Config?)
        with open('optimization_suggestions.txt', 'a') as f:
            f.write(f"{datetime.now().isoformat()}: {suggestions}\n")
    except Exception as e:
        print(f"LLM analysis failed: {e}. Ensure Ollama is running with model '{Config.OLLAMA_MODEL}'.")

    print("--- Examiner Complete ---")