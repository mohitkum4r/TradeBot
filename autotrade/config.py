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
    ADX_PERIOD = int(os.getenv("ADX_PERIOD", 14))
    TREND_THRESHOLD = int(os.getenv("TREND_THRESHOLD", 15))  # Lowered default
    STRONG_TREND_THRESHOLD = int(os.getenv("STRONG_TREND_THRESHOLD", 35))  # Lowered default
    VOL_BREAKOUT_WINDOW = int(os.getenv("VOL_BREAKOUT_WINDOW", 20))
    RSI_PERIOD = int(os.getenv("RSI_PERIOD", 14))
    RSI_DIVERGENCE_WINDOW = int(os.getenv("RSI_DIVERGENCE_WINDOW", 14))
    MA_SHORT_WINDOW = int(os.getenv("MA_SHORT_WINDOW", 10))  # Shorter for more signals
    MA_LONG_WINDOW = int(os.getenv("MA_LONG_WINDOW", 30))   # Shorter for more signals
    ENTRY_Z = float(os.getenv("ENTRY_Z", 1.5))  # Lower for more arbitrage trades
    VOLUME_MULTIPLIER = float(os.getenv("VOLUME_MULTIPLIER", 1.2))  # For signal confirmation
    RSI_BUY_THRESHOLD = int(os.getenv("RSI_BUY_THRESHOLD", 40))  # Buy only if RSI > this
    ADX_SELL_CONFIRM = int(os.getenv("ADX_SELL_CONFIRM", 25))  # Sell only if ADX > this (trending)
    COOLDOWN_AFTER_LOSS = int(os.getenv("COOLDOWN_AFTER_LOSS", 5))

    # New: Backtest Parameters (to avoid invalid interval/rate limits)
    BACKTEST_DAYS = int(os.getenv("BACKTEST_DAYS", 2))  # Increased to 2 years for more data
    BACKTEST_INTERVAL_MINUTES = int(os.getenv("BACKTEST_INTERVAL_MINUTES", 1))  # Finer interval
    FETCH_DELAY_SECONDS = float(os.getenv("FETCH_DELAY_SECONDS", 2.0))  # Delay between sequential fetches

    # New: API Interval Adjustment Mapping (accurate from Groww docs)
    INTERVAL_ADJUST_MAP = {
        1: 7,      # 1 min: 7 days
        5: 15,     # 5 min: 15 days
        10: 30,    # 10 min: 30 days
        60: 150,   # 1 hour: 150 days
        240: 365,  # 4 hours: 365 days
        1440: 1080, # 1 day: 1080 days (~3 years)
        10080: float('inf')  # 1 week: no limit (full history)
    }

    # New: Multi-Stock Trading Toggle
    MULTI_STOCK_TRADING_ENABLED = os.getenv("MULTI_STOCK_TRADING_ENABLED", True)  # Enable multi-stock signals

    # MODIFIED: Optimizations for profit maximization
    VOLUME_CONFIRMATION_MULTIPLIER = float(os.getenv("VOLUME_CONFIRMATION_MULTIPLIER", 1))  # For signal confirmation
    VWAP_WINDOW = int(os.getenv("VWAP_WINDOW", 20))  # For new VWAP strategy
    HEDGE_THRESHOLD = float(os.getenv("HEDGE_THRESHOLD", 0.05))  # For enhanced arbitrage

    # NEW: Dynamic universe (list of NSE tickers for screening via GrowwAPI)
    NSE_UNIVERSE = os.getenv("NSE_UNIVERSE", "RELIANCE,TCS,INFY,HDFCBANK,ICICIBANK,SBIN,AXISBANK,KOTAKBANK,INDUSINDBK,BAJFINANCE,BAJAJFINSV,WIPRO,HCLTECH,TECHM,MARUTI,M&M,HEROMOTOCO,EICHERMOT,TATAMOTORS,HINDALCO,JSWSTEEL,TATASTEEL,SUNPHARMA,DRREDDY,CIPLA,LUPIN,AUROPHARMA,DIVISLAB,ASIANPAINT,BERGEPAINT,ULTRACEMCO,GRASIM,HINDUNILVR,ITC,NESTLEIND,BRITANNIA,TATACONSUM,BPCL,HINDPETRO,ONGC,POWERGRID,NTPC,SBILIFE,HDFCLIFE").split(",")  # Expand this list as needed

    # NEW: For LLM examiner (use Mistral for analysis)
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")  # Changed default to Mistral for better suggestions
    EXAMINER_ENABLED = os.getenv("EXAMINER_ENABLED", True)  # Toggle for post-backtest analysis