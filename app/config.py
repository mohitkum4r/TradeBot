# app/config.py
import os
import logging

from dateutil import parser


class Config:
    # API and Authentication (all from [4])
    ACCESS_TOKEN = os.getenv("GROWW_ACCESS_TOKEN")
    # API_SECRET = os.getenv("GROWW_API_SECRET")
    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "AutoTradeBot/0.1")

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///autotrade.db")

    # Trading Configuration
    MODE = os.getenv("MODE", "PAPER")  # 'LIVE' or 'PAPER'
    MARKET_INDEX = os.getenv("MARKET_INDEX", "NIFTY")
    BACKTEST = os.getenv("BACKTEST", "False").lower() in ("true", "1", "t")
    POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", 3600))
    INITIAL_CAPITAL = float(os.getenv("INITIAL_CAPITAL", 100000.0))
    MAX_EXPOSURE_PER_TRADE = float(os.getenv("MAX_EXPOSURE_PER_TRADE", 0.2))
    RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", 0.01))
    STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", 0.05))
    TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", 0.10))

    # Strategies (all from [4])
    STOCKS = os.getenv("STOCKS", "RELIANCE,TCS,INFY,HDFCBANK,ICICIBANK").split(",")
    PAIRS_LIST = [  # List from [4]
        ["HDFCBANK", "ICICIBANK"],
        ["ICICIBANK", "AXISBANK"],
        ["HDFCBANK", "KOTAKBANK"],
        ["AXISBANK", "INDUSINDBK"],
        ["SBIN", "ICICIBANK"],
        ["BAJFINANCE", "BAJAJFINSV"],
        ["TCS", "INFY"],
        ["INFY", "WIPRO"],
        ["HCLTECH", "TECHM"],
        ["TCS", "HCLTECH"],
        ["MARUTI", "M&M"],
        ["HEROMOTOCO", "EICHERMOT"],
        ["TATAMOTORS", "M&M"],
        ["HINDALCO", "JSWSTEEL"],
        ["TATASTEEL", "JSWSTEEL"],
        ["SUNPHARMA", "DRREDDY"],
        ["CIPLA", "LUPIN"],
        ["AUROPHARMA", "CIPLA"],
        ["DIVISLAB", "DRREDDY"],
        ["ASIANPAINT", "BERGEPAINT"],
        ["ULTRACEMCO", "GRASIM"],
        ["HINDUNILVR", "ITC"],
        ["HINDUNILVR", "NESTLEIND"],
        ["BRITANNIA", "TATACONSUM"],
        ["BPCL", "HINDPETRO"],
        ["ONGC", "RELIANCE"],
        ["POWERGRID", "NTPC"],
        ["SBILIFE", "HDFCLIFE"],
    ]
    SENTIMENT_ANALYSIS_ENABLED = os.getenv(
        "SENTIMENT_ANALYSIS_ENABLED", "True"
    ).lower() in ("true", "1", "t")
    SENTIMENT_BUY_THRESHOLD = float(os.getenv("SENTIMENT_BUY_THRESHOLD", 0.2))
    SENTIMENT_SELL_THRESHOLD = float(os.getenv("SENTIMENT_SELL_THRESHOLD", -0.2))
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
    # Tax and Charges (from [4])
    STT_CHARGE = 0.001
    TRANSACTION_CHARGE = 0.0000325
    GST_ON_TRANSACTION_CHARGE = 0.18
    SEBI_CHARGE = 0.000001
    STAMP_DUTY = 0.00015
    # Strategy Parameters (from [4])
    ADX_PERIOD = int(os.getenv("ADX_PERIOD", 14))
    TREND_THRESHOLD = int(os.getenv("TREND_THRESHOLD", 15))
    STRONG_TREND_THRESHOLD = int(os.getenv("STRONG_TREND_THRESHOLD", 35))
    VOL_BREAKOUT_WINDOW = int(os.getenv("VOL_BREAKOUT_WINDOW", 20))
    RSI_PERIOD = int(os.getenv("RSI_PERIOD", 14))
    RSI_DIVERGENCE_WINDOW = int(os.getenv("RSI_DIVERGENCE_WINDOW", 14))
    MA_SHORT_WINDOW = int(os.getenv("MA_SHORT_WINDOW", 10))
    MA_LONG_WINDOW = int(os.getenv("MA_LONG_WINDOW", 30))
    ENTRY_Z = float(os.getenv("ENTRY_Z", 1.5))
    VOLUME_MULTIPLIER = float(os.getenv("VOLUME_MULTIPLIER", 1.2))
    RSI_BUY_THRESHOLD = int(os.getenv("RSI_BUY_THRESHOLD", 40))
    ADX_SELL_CONFIRM = int(os.getenv("ADX_SELL_CONFIRM", 25))
    COOLDOWN_AFTER_LOSS = int(os.getenv("COOLDOWN_AFTER_LOSS", 5))
    # Backtest Parameters (from [4])
    EXCHANGE = os.getenv("EXCHANGE", "NSE")
    SEGMENT = os.getenv("SEGMENT", "CASH")
    BACKTEST_DAYS = int(os.getenv("BACKTEST_DAYS", 2))
    BACKTEST_INTERVAL_MINUTES = int(os.getenv("BACKTEST_INTERVAL_MINUTES", 1))
    FETCH_DELAY_SECONDS = float(os.getenv("FETCH_DELAY_SECONDS", 2.0))
    INTERVAL_ADJUST_MAP = {
        1: 7,  # 1 min: 7 days
        5: 15,  # 5 min: 15 days
        10: 30,  # 10 min: 30 days
        60: 150,  # 1 hour: 150 days
        240: 365,  # 4 hours: 365 days
        1440: 1080,  # 1 day: 1080 days (~3 years)
        10080: float("inf"),  # 1 week: no limit (full history)
    }
    # Other (from [4])
    MULTI_STOCK_TRADING_ENABLED = os.getenv("MULTI_STOCK_TRADING_ENABLED", True)
    VOLUME_CONFIRMATION_MULTIPLIER = float(
        os.getenv("VOLUME_CONFIRMATION_MULTIPLIER", 1)
    )
    VWAP_WINDOW = int(os.getenv("VWAP_WINDOW", 20))
    HEDGE_THRESHOLD = float(os.getenv("HEDGE_THRESHOLD", 0.05))
    NSE_UNIVERSE = os.getenv("NSE_UNIVERSE", "").split(
        ","
    )  # Expand this list as needed
    EXAMINER_ENABLED = os.getenv("EXAMINER_ENABLED", True)
    BACKTEST_START_DATE = os.getenv("BACKTEST_START_DATE")  # e.g., "01-01-2023"
    BACKTEST_END_DATE = os.getenv("BACKTEST_END_DATE")      # e.g., "31-12-2023"

    @classmethod
    def validate(cls):
        required = ["ACCESS_TOKEN"] if cls.MODE == "LIVE" else []
        missing = [k for k in required if not getattr(cls, k, None)]
        if missing:
            raise ValueError(f"Missing required configs for {cls.MODE} mode: {missing}")
        # Type validations
        try:
            float(cls.INITIAL_CAPITAL)
            if cls.INITIAL_CAPITAL <= 0:
                raise ValueError("INITIAL_CAPITAL must be positive")
        except ValueError as e:
            raise ValueError(f"Config validation failed: {e}")
        if cls.BACKTEST:
            try:
                if cls.BACKTEST_START_DATE:
                    parser.parse(cls.BACKTEST_START_DATE)
                if cls.BACKTEST_END_DATE:
                    parser.parse(cls.BACKTEST_END_DATE)
            except ValueError as e:
                raise ValueError(f"Invalid backtestdir date format: {e}")
        logging.info("Configuration validated")


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
