# main.py
import logging
import schedule
import time
from growwapi import GrowwAPI
from app.config import Config
from app.container import container
from infrastructure.brokers.groww_broker import GrowwBrokerClient
from infrastructure.data_providers.groww_data_provider import GrowwDataProvider
from infrastructure.database.database import get_db, engine
from domain.models.models import create_all_tables
from infrastructure.data_providers.data_handler import DataHandler
from interfaces.i_data_provider import IDataProvider
from interfaces.i_broker_client import IBrokerClient
from interfaces.i_sentiment_analyzer import ISentimentAnalyzer
from interfaces.i_trade_logger import ITradeLogger
from interfaces.i_tax_calculator import ITaxCalculator
from use_cases.trade_executor import LiveTradeExecutor, PaperTradeExecutor
from domain.strategies.strategy_selector import StrategySelector
from use_cases.trading_cycle import trading_cycle
from use_cases.backtest import run_backtest

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def authenticate_groww(token: str) -> GrowwAPI | None:
    logging.info("Authenticating with Groww using token...")
    try:
        client = GrowwAPI(token=token)
        logging.info("Authentication successful")
        return client
    except Exception as e:
        logging.error(f"Authentication failed: {e}")
        return None


def main():
    logging.info("Initializing Trading Bot...")
    Config.validate()
    create_all_tables(engine)
    strategy = StrategySelector()

    # Token-based authentication (required for data provider even in backtestdir)
    token = Config.ACCESS_TOKEN  # Assume in config.py
    raw_client = authenticate_groww(token)
    if not raw_client:
        logging.error("Authentication failed. Aborting.")
        return

    # Register client-dependent services after authentication
    container.register(IDataProvider, lambda c: GrowwDataProvider(client=raw_client))
    container.register(IBrokerClient, lambda c: GrowwBrokerClient(client=raw_client))

    data_provider = container.get(IDataProvider)
    data_handler = DataHandler(data_provider=data_provider)
    sentiment_analyzer = container.get(ISentimentAnalyzer)
    logger = container.get(ITradeLogger)
    tax_calculator = container.get(ITaxCalculator)
    broker_client = container.get(IBrokerClient)

    if Config.BACKTEST:
        run_backtest(strategy, data_handler)
        return

    if Config.MODE == "LIVE":
        confirm = input("Confirm live trading with real money (y/n): ")
        if confirm.lower() != "y":
            logging.info("Live trading aborted")
            return
        executor = LiveTradeExecutor(
            data_handler=data_handler,
            logger=logger,
            tax_calculator=tax_calculator,
            client=broker_client,
        )
    else:
        executor = PaperTradeExecutor(
            data_handler=data_handler, logger=logger, tax_calculator=tax_calculator
        )

    logging.info(f"Bot running in '{Config.MODE}' mode.")

    with next(get_db()) as db_session:
        trading_cycle(
            db_session,
            data_handler,
            strategy,
            executor,
            sentiment_analyzer,
            Config.INITIAL_CAPITAL,
        )

    def scheduled_cycle():
        try:
            with next(get_db()) as db_session:
                trading_cycle(
                    db_session,
                    data_handler,
                    strategy,
                    executor,
                    sentiment_analyzer,
                    Config.INITIAL_CAPITAL,
                )
        except Exception as e:
            logging.error(f"Trading cycle failed: {e}")

    schedule.every(Config.POLL_INTERVAL_SECONDS).seconds.do(scheduled_cycle)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
