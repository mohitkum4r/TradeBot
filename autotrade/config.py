import os
from dotenv import load_dotenv

# Load environment variables from a .env file at the project root
load_dotenv()


def _get_env_bool(var_name: str, default: bool = False) -> bool:
    """Safely retrieves a boolean value from environment variables."""
    return os.getenv(var_name, str(default)).lower() in ("true", "1", "t")


def _get_env_list(var_name: str, default: str = "") -> list[str]:
    """Safely retrieves a list of strings from a comma-separated environment variable."""
    value = os.getenv(var_name, default)
    return [item.strip() for item in value.split(',') if item.strip()]


def _get_env_pairs(var_name: str, default: str = "") -> list[list[str]]:
    """
    Safely retrieves a list of stock pairs from a comma-separated,
    dash-delimited environment variable (e.g., "STOCKA-STOCKB,STOCKC-STOCKD").
    """
    value = os.getenv(var_name, default)
    pairs_str_list = [item.strip() for item in value.split(',') if item.strip()]
    parsed_pairs = []
    for pair_str in pairs_str_list:
        parts = [p.strip() for p in pair_str.split('-') if p.strip()]
        if len(parts) == 2:
            parsed_pairs.append(parts)
    return parsed_pairs


class Config:
    """
    Centralized configuration hub for the auto-trading application.
    It safely loads all settings from environment variables and provides
    sensible defaults to ensure stability and prevent accidental live trading.
    """

    # --- I. Execution Control ---
    # Defines the core operational mode of the bot.
    # 'PAPER' -> Simulates trades with live data. No real money involved.
    # 'LIVE' -> Executes real trades. USE WITH EXTREME CAUTION.
    MODE = os.getenv("MODE", "PAPER")

    # Determines whether to run a backtest on historical data or run the bot live/paper.
    # Defaults to True for safety, requiring explicit change to run the main bot.
    BACKTEST = _get_env_bool("BACKTEST", True)

    # The interval in seconds for the main trading loop to fetch data and check signals.
    POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", 60))

    # --- II. API Credentials ---
    # Your brokerage API credentials. These should be kept secret.
    API_KEY = os.getenv("API_KEY")
    API_SECRET = os.getenv("API_SECRET")

    # --- III. Trading & Risk Management ---
    # The list of NSE stock symbols the bot is allowed to trade.
    STOCKS = _get_env_list(
        "STOCKS", "RELIANCE,TCS,INFY,HDFCBANK,ICICIBANK,SBIN,AXISBANK"
    )

    # The total virtual capital available for trading.
    INITIAL_CAPITAL = float(os.getenv("INITIAL_CAPITAL", 100000.0))

    # The maximum percentage of capital to be allocated to any single trade.
    MAX_EXPOSURE_PER_TRADE = float(os.getenv("MAX_EXPOSURE_PER_TRADE", 0.1))

    # --- IV. Strategy & Model Configuration ---
    # The primary strategy to be used. 'AUTONOMOUS' is recommended as it dynamically
    # selects the best strategy based on market conditions.
    STRATEGY = os.getenv("STRATEGY", "AUTONOMOUS")

    # Default list of correlated stock pairs for the Pairs Trading Strategy.
    # This list is used if no `PAIRS_LIST` is specified in the .env file.
    DEFAULT_PAIRS = (
        "ICICIBANK-HDFCBANK,"
        "AXISBANK-KOTAKBANK,"
        "SBIN-HDFCBANK,"
        "TCS-INFY,"
        "HCLTECH-WIPRO,"
        "TATASTEEL-HINDALCO,"
        "RELIANCE-JIOFIN,"
        "PFC-RECLTD,"
        "TATAMOTORS-MARUTI,"
        "HAL-BDL"
    )
    PAIRS_LIST = _get_env_pairs("PAIRS_LIST", DEFAULT_PAIRS)

    # Path for the machine learning model file.
    ML_MODEL_PATH = os.getenv("ML_MODEL_PATH", "model.pkl")

    # --- V. Strategy-Specific Parameters ---
    # These can be fine-tuned in the .env file to optimize strategy performance.
    VOLATILITY_BREAKOUT_WINDOW = int(os.getenv("VOLATILITY_BREAKOUT_WINDOW", 20))
    VOLATILITY_BREAKOUT_MULTIPLIER = float(
        os.getenv("VOLATILITY_BREAKOUT_MULTIPLIER", 2.5)
    )
    RSI_DIVERGENCE_PERIOD = int(os.getenv("RSI_DIVERGENCE_PERIOD", 14))
    RSI_DIVERGENCE_LOOKBACK = int(os.getenv("RSI_DIVERGENCE_LOOKBACK", 20))

    # --- VI. Optional: Sentiment Analysis ---
    SENTIMENT_ANALYSIS_ENABLED = _get_env_bool("SENTIMENT_ANALYSIS_ENABLED", False)
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT = os.getenv(
        "REDDIT_USER_AGENT", "python:autotrade:v0.3.0 (by u/your_username)"
    )

    # --- VII. Miscellaneous ---
    # Database connection string.
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///trades.db")

    # Standard tax and charges for Indian markets (can be adjusted for accuracy).
    STT_CHARGE = 0.001
    TRANSACTION_CHARGE = 0.0000345
    GST_ON_TRANSACTION_CHARGE = 0.18
    SEBI_CHARGE = 10 / 1_00_00_000
    STAMP_DUTY = 0.00015

