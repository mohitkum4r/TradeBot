# autotrade/config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API and Authentication
    API_KEY = os.getenv("GROWW_API_KEY")
    API_SECRET = os.getenv("GROWW_API_SECRET")
    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "AutoTradeBot/0.1")

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///autotrade.db")

    # Trading Configuration
    MODE = os.getenv("MODE", "PAPER")  # 'LIVE' or 'PAPER'
    BACKTEST = os.getenv("BACKTEST", False)
    POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", 3600))  # 1 hour
    INITIAL_CAPITAL = float(os.getenv("INITIAL_CAPITAL", 100000.0))
    MAX_EXPOSURE_PER_TRADE = float(os.getenv("MAX_EXPOSURE_PER_TRADE", 0.2))  # 20% of capital
    RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", 0.01))  # 1% risk per trade
    STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", 0.05))  # 5% SL
    TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", 0.10))  # 10% TP

    # Strategies
    STOCKS = os.getenv("STOCKS", "RELIANCE,TCS,INFY,HDFCBANK,ICICIBANK").split(",")
    PAIRS_LIST = [
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
        ["SBILIFE", "HDFCLIFE"]
    ]  # Updated with user's provided pairs list
    SENTIMENT_ANALYSIS_ENABLED = os.getenv("SENTIMENT_ANALYSIS_ENABLED", True)
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama2")

    # Tax and Charges (Approximate for Indian Equity)
    STT_CHARGE = 0.001  # 0.1% on sell
    TRANSACTION_CHARGE = 0.0000325  # NSE + Broker
    GST_ON_TRANSACTION_CHARGE = 0.18  # 18%
    SEBI_CHARGE = 0.000001  # 0.0001%
    STAMP_DUTY = 0.00015  # 0.015% on buy

    # New: Strategy Parameters (for optimization)
    ADX_PERIOD = 14
    TREND_THRESHOLD = 25
    STRONG_TREND_THRESHOLD = 40
    VOL_BREAKOUT_WINDOW = 20
    RSI_PERIOD = 14
    RSI_DIVERGENCE_WINDOW = 14

    # New: Backtest Parameters (to avoid invalid interval/rate limits)
    BACKTEST_DAYS = int(os.getenv("BACKTEST_DAYS", 180))  # Default 180 days
    BACKTEST_INTERVAL_MINUTES = int(os.getenv("BACKTEST_INTERVAL_MINUTES", 1440))  # Default daily
    FETCH_DELAY_SECONDS = float(os.getenv("FETCH_DELAY_SECONDS", 2.0))  # Delay between sequential fetches