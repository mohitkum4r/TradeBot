# use_cases/backtest_executor.py
import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple
from app.config import Config
from infrastructure.tax.tax_calculator import TaxCalculator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def calculate_taxes(tax_calculator: TaxCalculator, value: float, action: str) -> float:
    dummy_trade = type('Trade', (), {
        'price': value / 100,
        'quantity': 100,
        'action': action,
        'stock': 'DUMMY'  # Placeholder to avoid AttributeError in logging
    })()  # Simplified dummy
    return tax_calculator.calculate_taxes(dummy_trade)  # Proper usage


def execute_backtest_loop(
    strategy, combined_df: pd.DataFrame, nifty_data: pd.DataFrame, stock_universe: list[str], min_length: int,
    initial_capital: float, tax_calculator: TaxCalculator
) -> Tuple[float, List[float], List[Dict], List[Dict], float]:
    cash = initial_capital
    pending_cash: List[Dict[str, float]] = []
    positions: Dict[str, int] = {stock: 0 for stock in stock_universe}
    buy_prices: Dict[str, float] = {stock: 0.0 for stock in stock_universe}
    peak_prices: Dict[str, float] = {stock: 0.0 for stock in stock_universe}
    hedge_pairs: Dict[str, str] = {}  # long_stock -> short_stock
    daily_values: List[float] = []
    trades: List[Dict] = []
    detailed_logs: List[Dict] = []
    steps_per_day = int(390 / Config.BACKTEST_INTERVAL_MINUTES) if Config.BACKTEST_INTERVAL_MINUTES > 0 else 1
    cumulative_ideal_pnl = 0.0

    for i in range(1, min_length):
        current_slice = combined_df.iloc[:i].copy()
        current_nifty_slice = nifty_data.iloc[:i].copy()

        # Release pending cash
        pending_to_release = [p for p in pending_cash if p["release_step"] <= i]
        for p in pending_to_release:
            cash += p["amount"]
            pending_cash.remove(p)
            logging.info(f"Released pending cash ₹{p['amount']:.2f} at step {i}")

        # Generate signals
        try:
            signals = strategy.generate_signal(current_nifty_slice, full_stock_data=current_slice)
            if not isinstance(signals, list):
                signals = [signals] if signals else []
        except Exception as e:
            logging.error(f"Signal generation failed at step {i}: {e}")
            signals = []

        # Features and optimal signals
        from .backtest_data import calculate_indicators, get_optimal_signal
        features = {}
        optimal_signals = {}
        for stock in stock_universe:
            stock_data = current_slice[stock] if isinstance(current_slice.columns, pd.MultiIndex) and stock in current_slice.columns.levels[0] else pd.DataFrame()
            features[stock] = calculate_indicators(stock_data)
            optimal_signals[stock] = get_optimal_signal(stock_data, i)

        # Log step
        step_log = {
            "step": i,
            "signals": signals,
            "features": features,
            "optimal_signals": optimal_signals,
            "positions": positions.copy(),
            "cash": cash,
            "market_snapshot": {stock: current_slice[stock].iloc[-1].to_dict() if isinstance(current_slice.columns, pd.MultiIndex) and stock in current_slice.columns.levels[0] else {} for stock in stock_universe}
        }
        detailed_logs.append(step_log)

        # Ideal PnL
        step_ideal_pnl = 0.0
        for stock in stock_universe:
            stock_slice = current_slice[stock] if isinstance(current_slice.columns, pd.MultiIndex) and stock in current_slice.columns.levels[0] else pd.DataFrame()
            if len(stock_slice) < 2:
                continue
            min_price = stock_slice["low"].min()
            max_price = stock_slice["high"].max()
            min_price = min_price if not pd.isna(min_price) else 0.0
            max_price = max_price if not pd.isna(max_price) else 0.0
            if min_price >= max_price or min_price == 0:
                continue
            qty = int(initial_capital * Config.MAX_EXPOSURE_PER_TRADE / min_price)
            buy_cost = min_price * qty * 1.001
            sell_revenue = max_price * qty * 0.999
            taxes = calculate_taxes(tax_calculator, buy_cost, "BUY") + calculate_taxes(tax_calculator, sell_revenue, "SELL")
            ideal_profit = sell_revenue - buy_cost - taxes
            step_ideal_pnl += ideal_profit
        cumulative_ideal_pnl += step_ideal_pnl

        # Process signals
        for signal_tuple in signals:
            if len(signal_tuple) != 3:
                continue
            stock, signal, reason = signal_tuple
            if stock not in stock_universe or not isinstance(current_slice.columns, pd.MultiIndex) or stock not in current_slice.columns.levels[0]:
                continue
            current_price = current_slice[(stock, "close")].iloc[-1] if len(current_slice[(stock, "close")]) > 0 else 0.0
            if pd.isna(current_price) or current_price <= 0:
                continue

            atr = features[stock]["atr"]
            position_size = int((cash * Config.RISK_PER_TRADE) / atr) if atr > 0 else 0

            if signal == "BUY" and positions[stock] == 0:
                capital_to_use = min(cash * Config.MAX_EXPOSURE_PER_TRADE, cash * Config.RISK_PER_TRADE)
                quantity = min(position_size, int(capital_to_use / current_price))
                if quantity > 0:
                    cost = current_price * quantity * 1.001
                    taxes = calculate_taxes(tax_calculator, cost, "BUY")
                    if cash >= cost + taxes:
                        cash -= cost + taxes
                        positions[stock] = quantity
                        buy_prices[stock] = current_price
                        peak_prices[stock] = current_price
                        logging.info(f"BUY {quantity} {stock} @ {current_price:.2f} | Reason: {reason}")
                        trades.append({"stock": stock, "entry_price": current_price, "quantity": quantity, "entry_step": i, "taxes": taxes})

            elif signal == "SELL" and positions[stock] > 0:
                revenue = current_price * positions[stock] * 0.999
                taxes = calculate_taxes(tax_calculator, revenue, "SELL")
                total_revenue = revenue - taxes
                release_step = i + steps_per_day
                pending_cash.append({"amount": total_revenue, "release_step": release_step})
                pnl = (current_price - buy_prices[stock]) * positions[stock] - taxes
                trade_type = "win" if pnl > 0 else "loss"
                logging.info(f"SELL {positions[stock]} {stock} @ {current_price:.2f} | PnL: {pnl:.2f} | Reason: {reason}")
                trades.append({"stock": stock, "exit_price": current_price, "pnl": pnl, "type": trade_type, "exit_step": i, "taxes": taxes})
                positions[stock] = 0

            elif signal == "BUY_SPREAD" and positions[stock] == 0:
                # Logical hedge: Assume reason includes paired stock (e.g., from pairs strategy)
                # Parse paired_stock from reason or assume first pair from Config.PAIRS_LIST containing stock
                paired_stock = None
                for pair in Config.PAIRS_LIST:
                    if stock in pair:
                        paired_stock = pair[0] if pair[1] == stock else pair[1]
                        break
                if not paired_stock or paired_stock not in stock_universe:
                    logging.warning(f"No valid pair for {stock} in BUY_SPREAD")
                    continue
                paired_price = (
                    current_slice[(paired_stock, "close")].iloc[-1]
                    if len(current_slice[(paired_stock, "close")]) > 0
                    else 0.0
                )
                if pd.isna(paired_price) or paired_price <= 0:
                    continue

                # Buy main stock, short paired stock (hedge)
                capital_to_use = min(
                    cash * Config.MAX_EXPOSURE_PER_TRADE, cash * Config.RISK_PER_TRADE
                )
                long_qty = min(position_size, int(capital_to_use / current_price))
                short_qty = int(
                    long_qty * (current_price / paired_price)
                )  # Ratio hedge

                if long_qty > 0 and short_qty > 0:
                    long_cost = current_price * long_qty * 1.001
                    short_revenue = paired_price * short_qty * 0.999  # Short sell
                    taxes = calculate_taxes(
                        tax_calculator, long_cost, "BUY"
                    ) + calculate_taxes(tax_calculator, short_revenue, "SELL")
                    net_cost = long_cost - short_revenue + taxes
                    if cash >= net_cost:
                        cash -= net_cost
                        positions[stock] = long_qty
                        positions[paired_stock] = -short_qty  # Negative for short
                        buy_prices[stock] = current_price
                        buy_prices[paired_stock] = paired_price
                        peak_prices[stock] = current_price
                        peak_prices[paired_stock] = paired_price
                        hedge_pairs[stock] = paired_stock
                        logging.info(
                            f"BUY_SPREAD: BUY {long_qty} {stock} @ {current_price:.2f}, SELL {short_qty} {paired_stock} @ {paired_price:.2f} | Reason: {reason}"
                        )
                        trades.append(
                            {
                                "stock": stock,
                                "entry_price": current_price,
                                "quantity": long_qty,
                                "entry_step": i,
                                "taxes": taxes,
                                "hedge": paired_stock,
                            }
                        )

            elif (
                signal == "SELL_SPREAD"
                and positions[stock] > 0
                and stock in hedge_pairs
            ):
                paired_stock = hedge_pairs[stock]
                if (
                    paired_stock not in positions or positions[paired_stock] >= 0
                ):  # Ensure short position
                    continue
                paired_price = (
                    current_slice[(paired_stock, "close")].iloc[-1]
                    if len(current_slice[(paired_stock, "close")]) > 0
                    else 0.0
                )
                if pd.isna(paired_price) or paired_price <= 0:
                    continue

                # Sell main stock, buy back paired (close short)
                long_qty = positions[stock]
                short_qty = abs(positions[paired_stock])
                long_revenue = current_price * long_qty * 0.999
                short_cost = paired_price * short_qty * 1.001  # Buy to cover
                taxes = calculate_taxes(
                    tax_calculator, long_revenue, "SELL"
                ) + calculate_taxes(tax_calculator, short_cost, "BUY")
                total_revenue = long_revenue - short_cost - taxes
                release_step = i + steps_per_day
                pending_cash.append(
                    {"amount": total_revenue, "release_step": release_step}
                )
                pnl = (
                    ((current_price - buy_prices[stock]) * long_qty)
                    + ((buy_prices[paired_stock] - paired_price) * short_qty)
                    - taxes
                )  # Profit from long + short
                trade_type = "win" if pnl > 0 else "loss"
                logging.info(
                    f"SELL_SPREAD: SELL {long_qty} {stock} @ {current_price:.2f}, BUY {short_qty} {paired_stock} @ {paired_price:.2f} | PnL: {pnl:.2f} | Reason: {reason}"
                )
                trades.append(
                    {
                        "stock": stock,
                        "exit_price": current_price,
                        "pnl": pnl,
                        "type": trade_type,
                        "exit_step": i,
                        "taxes": taxes,
                        "hedge": paired_stock,
                    }
                )
                positions[stock] = 0
                positions[paired_stock] = 0
                del hedge_pairs[stock]

            elif signal == "EXIT_SPREAD" and stock in hedge_pairs:
                # Similar to SELL_SPREAD, but force exit regardless of profit
                paired_stock = hedge_pairs[stock]
                if paired_stock not in positions:
                    continue
                paired_price = (
                    current_slice[(paired_stock, "close")].iloc[-1]
                    if len(current_slice[(paired_stock, "close")]) > 0
                    else 0.0
                )
                if pd.isna(paired_price) or paired_price <= 0:
                    continue

                long_qty = positions[stock] if positions[stock] > 0 else 0
                short_qty = (
                    abs(positions[paired_stock]) if positions[paired_stock] < 0 else 0
                )
                long_revenue = current_price * long_qty * 0.999 if long_qty > 0 else 0
                short_cost = paired_price * short_qty * 1.001 if short_qty > 0 else 0
                taxes = calculate_taxes(
                    tax_calculator, long_revenue, "SELL"
                ) + calculate_taxes(tax_calculator, short_cost, "BUY")
                total_revenue = long_revenue - short_cost - taxes
                release_step = i + steps_per_day
                pending_cash.append(
                    {"amount": total_revenue, "release_step": release_step}
                )
                pnl = (
                    ((current_price - buy_prices[stock]) * long_qty)
                    + ((buy_prices[paired_stock] - paired_price) * short_qty)
                    - taxes
                )
                trade_type = "win" if pnl > 0 else "loss"
                logging.info(
                    f"EXIT_SPREAD: SELL {long_qty} {stock} @ {current_price:.2f}, BUY {short_qty} {paired_stock} @ {paired_price:.2f} | PnL: {pnl:.2f} | Reason: {reason}"
                )
                trades.append(
                    {
                        "stock": stock,
                        "exit_price": current_price,
                        "pnl": pnl,
                        "type": trade_type,
                        "exit_step": i,
                        "taxes": taxes,
                        "hedge": paired_stock,
                    }
                )
                positions[stock] = 0
                positions[paired_stock] = 0
                del hedge_pairs[stock]

        # Trailing stop and take-profit (applied to both single and hedged positions)
        for stock in list(positions.keys()):
            if (
                positions[stock] > 0
                and isinstance(current_slice.columns, pd.MultiIndex)
                and stock in current_slice.columns.levels[0]
            ):
                current_price = (
                    current_slice[(stock, "close")].iloc[-1]
                    if len(current_slice[(stock, "close")]) > 0
                    else 0.0
                )
                if pd.isna(current_price) or current_price <= 0:
                    continue
                peak_prices[stock] = max(peak_prices[stock], current_price)
                if current_price < peak_prices[stock] * (1 - Config.STOP_LOSS_PCT):
                    revenue = current_price * positions[stock] * 0.999
                    taxes = calculate_taxes(tax_calculator, revenue, "SELL")
                    total_revenue = revenue - taxes
                    release_step = i + steps_per_day
                    pending_cash.append(
                        {"amount": total_revenue, "release_step": release_step}
                    )
                    pnl = (current_price - buy_prices[stock]) * positions[stock] - taxes
                    logging.info(
                        f"TRAILING STOP SELL {positions[stock]} {stock} @ {current_price:.2f} | PnL: {pnl:.2f}"
                    )
                    trades.append(
                        {
                            "stock": stock,
                            "exit_price": current_price,
                            "pnl": pnl,
                            "type": "stop_loss",
                            "exit_step": i,
                            "taxes": taxes,
                        }
                    )
                    positions[stock] = 0
                    # If hedged, close pair as well
                    if stock in hedge_pairs:
                        paired_stock = hedge_pairs[stock]
                        paired_price = (
                            current_slice[(paired_stock, "close")].iloc[-1]
                            if len(current_slice[(paired_stock, "close")]) > 0
                            else 0.0
                        )
                        if pd.isna(paired_price) or paired_price <= 0:
                            continue
                        short_qty = abs(positions[paired_stock])
                        short_cost = paired_price * short_qty * 1.001
                        short_taxes = calculate_taxes(tax_calculator, short_cost, "BUY")
                        total_revenue -= short_cost + short_taxes
                        pending_cash[-1][
                            "amount"
                        ] = total_revenue  # Adjust previous pending
                        paired_pnl = (
                            buy_prices[paired_stock] - paired_price
                        ) * short_qty - short_taxes
                        pnl += paired_pnl
                        logging.info(
                            f"Closing hedge: BUY {short_qty} {paired_stock} @ {paired_price:.2f} | Additional PnL: {paired_pnl:.2f}"
                        )
                        trades[-1]["pnl"] = pnl
                        trades[-1]["hedge"] = paired_stock
                        positions[paired_stock] = 0
                        del hedge_pairs[stock]
                elif current_price > buy_prices[stock] * (1 + Config.TAKE_PROFIT_PCT):
                    revenue = current_price * positions[stock] * 0.999
                    taxes = calculate_taxes(tax_calculator, revenue, "SELL")
                    total_revenue = revenue - taxes
                    release_step = i + steps_per_day
                    pending_cash.append(
                        {"amount": total_revenue, "release_step": release_step}
                    )
                    pnl = (current_price - buy_prices[stock]) * positions[stock] - taxes
                    logging.info(
                        f"TAKE PROFIT SELL {positions[stock]} {stock} @ {current_price:.2f} | PnL: {pnl:.2f}"
                    )
                    trades.append(
                        {
                            "stock": stock,
                            "exit_price": current_price,
                            "pnl": pnl,
                            "type": "take_profit",
                            "exit_step": i,
                            "taxes": taxes,
                        }
                    )
                    positions[stock] = 0
                    # Similar hedge close as above if in hedge_pairs

        # Portfolio value
        portfolio_value = cash + sum(
            positions[s] * current_slice[(s, "close")].iloc[-1] if isinstance(current_slice.columns, pd.MultiIndex) and s in current_slice.columns.levels[0] and len(current_slice[(s, "close")]) > 0 else 0
            for s in stock_universe
        )
        daily_values.append(portfolio_value)

    # Finalize
    for p in pending_cash:
        cash += p["amount"]
    final_portfolio_value = cash + sum(
        positions[s] * combined_df[(s, "close")].iloc[-1] if isinstance(combined_df.columns, pd.MultiIndex) and s in combined_df.columns.levels[0] and len(combined_df[(s, "close")]) > 0 else 0
        for s in stock_universe
    )

    return final_portfolio_value, daily_values, trades, detailed_logs, cumulative_ideal_pnl
