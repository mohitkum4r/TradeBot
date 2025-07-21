# use_cases/backtest.py
from datetime import datetime
import pandas as pd
import numpy as np
import logging
from domain.strategies.base_strategy import BaseStrategy
from infrastructure.data_providers.data_handler import DataHandler
from app.config import Config
from app.container import container
from infrastructure.stock_screener.stock_screener import StockScreener
from interfaces.i_tax_calculator import ITaxCalculator
from .backtestdir.backtest_data import fetch_backtest_data
from .backtestdir.backtest_executor import execute_backtest_loop
from .backtestdir.backtest_analyzer import train_ml_on_optimal, examine_backtest

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def run_backtest(strategy: BaseStrategy, data_handler: DataHandler):
    logging.info(f"Starting backtest for {strategy.__class__.__name__}")
    tax_calculator = container.get(ITaxCalculator)
    screener = container.get(StockScreener)  # Inject screener

    # Screen stocks first
    screened_stocks = screener.screen_for_momentum()
    if not screened_stocks:
        logging.warning("No momentum stocks found; using all stocks as fallback.")
        screened_stocks = Config.STOCKS  # Fallback
    Config.STOCKS = screened_stocks  # Update config dynamically

    historical_data, nifty_data, combined_df, stock_universe, min_length = fetch_backtest_data(data_handler)
    if not historical_data:
        return

    initial_capital = Config.INITIAL_CAPITAL
    final_portfolio_value, daily_values, trades, detailed_logs, cumulative_ideal_pnl = execute_backtest_loop(
        strategy, combined_df, nifty_data, stock_universe, min_length, initial_capital, tax_calculator
    )

    # Metrics
    returns = pd.Series(daily_values).pct_change().dropna()
    total_pnl = final_portfolio_value - initial_capital
    total_pnl_percent = (
        (total_pnl / initial_capital * 100) if initial_capital > 0 else 0
    )
    sharpe_ratio = (
        (returns.mean() / returns.std() * np.sqrt(252)) if returns.std() != 0 else 0
    )
    max_drawdown = (
        ((returns + 1).cumprod().cummax() - (returns + 1).cumprod()).max()
        if not returns.empty
        else 0
    )
    win_rate = (
        len([t for t in trades if t.get("pnl", 0) > 0]) / len(trades) if trades else 0
    )
    avg_win = (
        np.mean([t["pnl"] for t in trades if t.get("pnl", 0) > 0])
        if any(t.get("pnl", 0) > 0 for t in trades)
        else 0
    )
    avg_loss = (
        np.mean([t["pnl"] for t in trades if t.get("pnl", 0) < 0])
        if any(t.get("pnl", 0) < 0 for t in trades)
        else 0
    )
    profit_factor = (
        abs(
            sum(t["pnl"] for t in trades if t.get("pnl", 0) > 0)
            / sum(abs(t["pnl"]) for t in trades if t.get("pnl", 0) < 0)
        )
        if any(t.get("pnl", 0) < 0 for t in trades)
        else float("inf")
    )
    total_trades = len(trades)
    total_taxes = sum(t.get("taxes", 0) for t in trades)

    performance_log = {
        "timestamp": datetime.now().isoformat(),
        "strategy": strategy.__class__.__name__,
        "initial_capital": initial_capital,
        "final_portfolio_value": final_portfolio_value,
        "total_pnl": total_pnl,
        "total_pnl_percent": total_pnl_percent,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
        "total_trades": total_trades,
        "total_taxes": total_taxes,
        "cumulative_ideal_pnl": cumulative_ideal_pnl,
    }
    logging.info(f"Backtest Results: {performance_log}")

    train_ml_on_optimal(detailed_logs)
    if Config.EXAMINER_ENABLED:
        examine_backtest(performance_log, historical_data)

    logging.info("Backtest complete")
