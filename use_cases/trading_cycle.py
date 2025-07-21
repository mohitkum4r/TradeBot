# use_cases/trading_cycle.py
import logging
from app.container import container
from infrastructure.stock_screener.stock_screener import StockScreener
from app.config import Config
from utilities.date_utils import parse_backtest_dates  # Use utility for date handling

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def trading_cycle(db_session, data_handler, strategy, executor, sentiment_analyzer, current_capital):
    logging.info("Starting Trading Cycle")
    screener = container.get(StockScreener)  # Inject screener
    screened_stocks = screener.screen_for_momentum()
    Config.STOCKS = screened_stocks  # Filter stocks

    try:
        start_dt, end_dt, _ = parse_backtest_dates(Config)  # Use utility to avoid duplicacy
        market_index_data = data_handler.get_historical_data(
            Config.MARKET_INDEX, Config.BACKTEST_INTERVAL_MINUTES, start_dt, end_dt
        )
        if market_index_data.empty:
            logging.warning("No market index data")
            return

        stocks_data = data_handler.get_multiple_stocks_data(
            Config.STOCKS, Config.BACKTEST_INTERVAL_MINUTES, start_dt, end_dt
        )
        valid_stocks_data = {k: v for k, v in stocks_data.items() if not v.empty}
        if not valid_stocks_data:
            logging.warning("No valid stock data")
            return

        signals = strategy.generate_signal(market_index_data, full_stock_data=valid_stocks_data)
        if not isinstance(signals, list):
            signals = [signals] if signals else []

        for signal_tuple in signals:
            if len(signal_tuple) != 3:
                continue
            stock, action, reason = signal_tuple
            if action not in ["BUY", "SELL"]:
                logging.info(f"Holding {stock}. Reason: {reason}")
                continue

            if Config.SENTIMENT_ANALYSIS_ENABLED:
                sentiment = sentiment_analyzer.get_sentiment_score(stock)
                if (action == "BUY" and sentiment < Config.SENTIMENT_BUY_THRESHOLD) or (
                    action == "SELL" and sentiment > Config.SENTIMENT_SELL_THRESHOLD
                ):
                    logging.info(f"{action} vetoed by sentiment {sentiment:.2f} for {stock}")
                    continue

            ltp = data_handler.get_ltp(stock)
            if ltp <= 0:
                logging.warning(f"Invalid LTP {ltp} for {stock}")
                continue
            max_qty = int((current_capital * Config.MAX_EXPOSURE_PER_TRADE) / ltp)
            if max_qty <= 0:
                logging.warning(f"Insufficient capital for {stock}")
                continue

            executor.execute_trade(db_session, stock, action, max_qty, reason, current_capital)

    except Exception as e:
        logging.error(f"Trading cycle error: {e}")
    logging.info("Trading Cycle Finished")
