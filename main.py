# main.py
import schedule
import time
import pyotp
import pandas as pd
from sqlalchemy.orm import Session
from growwapi import GrowwAPI
from growwapi.groww.exceptions import GrowwAPIException

from autotrade.config import Config
from autotrade.database import get_db, engine
from autotrade import models
from autotrade.services.data_handler import DataHandler
from autotrade.services.trade_executor import (
    LiveTradeExecutor,
    PaperTradeExecutor,
    BaseTradeExecutor,
)
from autotrade.services.sentiment_analyzer import SentimentAnalyzer
from autotrade.strategies.base_strategy import BaseStrategy
from autotrade.strategies.strategy_selector import StrategySelector
from backtest import run_backtest


def authenticate_groww() -> GrowwAPI | None:
    """Authenticates with Groww using API Key and TOTP."""
    print("Authenticating with Groww...")
    if not Config.API_KEY or not Config.API_SECRET:
        print("Error: API_KEY and API_SECRET must be set in the .env file.")
        return None
    try:
        totp_gen = pyotp.TOTP(Config.API_SECRET)
        totp = totp_gen.now()
        token = GrowwAPI.get_access_token(api_key=Config.API_KEY, totp=totp)
        client = GrowwAPI(token=token)
        print("✅ Authentication Successful!")
        return client
    except GrowwAPIException as e:
        print(f"❌ Authentication Failed: {e}")
        return None
    except Exception as e:
        print(f"❌ An unexpected error occurred during authentication: {e}")
        return None


def select_strategy() -> BaseStrategy:
    """Factory function to select and instantiate the strategy."""
    # This application is now designed to run autonomously.
    # We will always use the StrategySelector.
    # Manual selection can be done by modifying this function if needed.
    print("📈 Strategy loaded: Autonomous StrategySelector (Regime Filter)")
    return StrategySelector()


def trading_cycle(
    db: Session,
    data_handler: DataHandler,
    strategy: BaseStrategy,
    executor: BaseTradeExecutor,
    sentiment_analyzer: SentimentAnalyzer | None,
):
    print(
        "\n"
        + "=" * 20
        + f" New Trading Cycle: {time.strftime('%Y-%m-%d %H:%M:%S')} "
        + "=" * 20
    )

    try:
        # --- Regime Analysis & Signal Generation ---
        print("--- Performing Global Market Regime Analysis ---")
        # Use Nifty 50 as the benchmark for overall market conditions
        # Note: In a production system, you might cache this data to reduce API calls.
        nifty_data = data_handler.get_historical_data("^NSEI", days=250)
        if nifty_data.empty:
            print("Could not fetch Nifty 50 data. Skipping cycle.")
            return

        # Fetch data for all stocks at once for portfolio/pairs strategies
        all_stock_data = {}
        stock_universe = list(set(Config.STOCKS + [item for pair in Config.PAIRS_LIST for item in pair]))
        for stock in stock_universe:
            # Fetch slightly more data for momentum calculations
            all_stock_data[stock] = data_handler.get_historical_data(stock, days=250)

        # Combine into a single multi-column DataFrame
        full_df = pd.concat(all_stock_data, axis=1)

        # Get the current portfolio state to help strategies make decisions
        current_portfolio_stocks = [p.stock for p in db.query(models.Portfolio).all()]

        # Generate trading signals using the autonomous selector
        trade_signals = strategy.generate_signal(
            data=nifty_data,
            full_stock_data=full_df,
            current_portfolio=current_portfolio_stocks,
        )

        # --- Signal Execution ---
        if not trade_signals:
            print("No trading signals generated in this cycle.")
            return

        # Get current capital for risk management
        current_capital = Config.INITIAL_CAPITAL  # TODO: Query from DB for live updates

        # The selector might return a single tuple or a list of tuples
        if isinstance(trade_signals, list):
            # For portfolio rebalancing
            for stock, signal, reason in trade_signals:
                # Dynamic quantity based on config and risk
                max_qty = int((current_capital * Config.MAX_EXPOSURE_PER_TRADE) / data_handler.get_ltp(stock) or 1)
                executor.execute_trade(stock, signal, max_qty, reason, current_capital)
        elif isinstance(trade_signals, tuple):
            # For single trades or pairs
            instrument, signal, reason = trade_signals
            if signal == "HOLD":
                print(f"Signal is HOLD. Reason: {reason}")
            elif "SPREAD" in signal:
                # Handle pairs trade
                stock1, stock2 = instrument.split(',')
                max_qty = int((current_capital * Config.MAX_EXPOSURE_PER_TRADE) / data_handler.get_ltp(stock1) or 1)
                if signal == "BUY_SPREAD":  # Long stock1, Short stock2
                    print("Executing BUY SPREAD")
                    executor.execute_trade(stock1, "BUY", max_qty, reason, current_capital)
                    # executor.execute_trade(stock2, "SELL", max_qty, reason, current_capital)  # Shorting requires specific setup
                elif signal == "SELL_SPREAD":  # Short stock1, Long stock2
                    print("Executing SELL SPREAD")
                    # executor.execute_trade(stock1, "SELL", max_qty, reason, current_capital)
                    executor.execute_trade(stock2, "BUY", max_qty, reason, current_capital)
            else:
                # Handle single instrument trade (e.g., from Dual MA Crossover)
                max_qty = int((current_capital * Config.MAX_EXPOSURE_PER_TRADE) / data_handler.get_ltp(instrument) or 1)
                executor.execute_trade(instrument, signal, max_qty, reason, current_capital)

    except Exception as e:
        print(f"An error occurred during the trading cycle: {e}")
        import traceback
        traceback.print_exc()


def main():
    print("🚀 Initializing Trading Bot...")
    models.create_all_tables(engine)

    # The bot now exclusively uses the autonomous selector
    strategy = select_strategy()

    # Authenticate regardless of mode (required for Groww API in backtest)
    client = authenticate_groww()
    if not client:
        print("Authentication failed. Aborting.")
        return

    data_handler = DataHandler(client=client)

    if Config.BACKTEST:
        run_backtest(strategy, data_handler)
        return

    sentiment_analyzer = SentimentAnalyzer()

    with get_db() as db_session:
        if Config.MODE == "LIVE":
            executor = LiveTradeExecutor(
                db=db_session, data_handler=data_handler, client=client
            )
        else:
            executor = PaperTradeExecutor(
                db=db_session, data_handler=data_handler, client=client
            )

        print(f"🤖 Bot running in '{Config.MODE}' mode with autonomous strategy selection.")

        # Run the first trading cycle immediately
        trading_cycle(
            db_session, data_handler, strategy, executor, sentiment_analyzer
        )

        # Schedule subsequent cycles
        schedule.every(Config.POLL_INTERVAL_SECONDS).seconds.do(
            trading_cycle,
            db_session,
            data_handler,
            strategy,
            executor,
            sentiment_analyzer,
        )

        while True:
            schedule.run_pending()
            time.sleep(1)


if __name__ == "__main__":
    main()