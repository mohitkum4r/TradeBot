import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """
    Centralized configuration for the application.
    Loads settings from environment variables.
    """

    # --- Application Settings ---
    MODE = os.getenv("MODE", "PAPER")  # 'LIVE' or 'PAPER'
    BACKTEST = os.getenv("BACKTEST", "False").lower() in ("true", "1")
    POLL_INTERVAL_SECONDS = int(
        os.getenv("POLL_INTERVAL_SECONDS", 300)
    )  # Interval for trading cycle

    # --- Trading Parameters ---
    STOCKS = os.getenv("STOCKS", "RELIANCE,TCS,INFY,HDFCBANK,ICICIBANK").split(",")
    INITIAL_CAPITAL = float(os.getenv("INITIAL_CAPITAL", 100000.0))
    MAX_EXPOSURE_PER_TRADE = float(
        os.getenv("MAX_EXPOSURE_PER_TRADE", 0.1)
    )  # 10% of capital per trade
    STOP_LOSS_PERCENT = float(os.getenv("STOP_LOSS_PERCENT", 0.02))  # 2% stop loss
    TAKE_PROFIT_PERCENT = float(
        os.getenv("TAKE_PROFIT_PERCENT", 0.05)
    )  # 5% take profit
    USE_TRAILING_STOP = os.getenv("USE_TRAILING_STOP", "True").lower() in ("true", "1")
    TRAILING_STOP_PERCENT = float(
        os.getenv("TRAILING_STOP_PERCENT", 0.015)
    )  # 1.5% trailing stop

    # --- Database ---
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///trades.db")

    # --- Groww API Authentication ---
    API_KEY = os.getenv("API_KEY")
    API_SECRET = os.getenv("API_SECRET")

    # --- Sentiment Analysis ---
    SENTIMENT_ANALYSIS_ENABLED = os.getenv(
        "SENTIMENT_ANALYSIS_ENABLED", "False"
    ).lower() in ("true", "1")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT = os.getenv(
        "REDDIT_USER_AGENT", "python:autotrade:v0.3.0 (by /u/your_username)"
    )

    # --- Tax Configuration (for Indian markets) ---
    STT_CHARGE = 0.001  # Example value for delivery sell
    TRANSACTION_CHARGE = 0.0000345  # Example for NSE
    GST_ON_TRANSACTION_CHARGE = 0.18
    SEBI_CHARGE = 10 / 1_00_00_000
    STAMP_DUTY = 0.00015  # Example for buy orders

    # --- Strategy Configuration ---
    # Main strategy selector switch. 'AUTONOMOUS' is recommended.
    # Options: 'AUTONOMOUS', 'MOMENTUM', 'MEAN_REVERSION', 'DUAL_MA_CROSSOVER', etc.
    STRATEGY = os.getenv("STRATEGY", "AUTONOMOUS")

    # --- Pairs Trading ---
    PAIRS_LIST = [
        p.split('-') for p in os.getenv("PAIRS_LIST", "ICICIBANK-HDFCBANK,RELIANCE-TCS").split(',')
    ]


    # --- Volatility Breakout Strategy ---
    VOLATILITY_BREAKOUT_WINDOW = int(os.getenv("VOLATILITY_BREAKOUT_WINDOW", 20))
    VOLATILITY_BREAKOUT_MULTIPLIER = float(os.getenv("VOLATILITY_BREAKOUT_MULTIPLIER", 2.5))

    # --- RSI Divergence ---
    RSI_DIVERGENCE_PERIOD = int(os.getenv("RSI_DIVERGENCE_PERIOD", 14))
    RSI_DIVERGENCE_LOOKBACK = int(os.getenv("RSI_DIVERGENCE_LOOKBACK", 20))


    # --- ML Strategy ---
    ML_MODEL_PATH = os.getenv("ML_MODEL_PATH", "model.pkl")