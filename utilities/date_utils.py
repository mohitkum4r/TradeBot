# utilities/date_utils.py (New file to centralize date parsing and avoid duplicacy)
from datetime import datetime, timedelta
from dateutil import parser
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_backtest_dates(config):
    today = datetime.now().strftime("%Y-%m-%d")
    if config.BACKTEST_START_DATE and config.BACKTEST_END_DATE:
        try:
            start_dt = parser.parse(config.BACKTEST_START_DATE).strftime("%Y-%m-%d")
            end_dt = parser.parse(config.BACKTEST_END_DATE).strftime("%Y-%m-%d")
            start_time_dt = datetime.strptime(start_dt, "%Y-%m-%d")
            end_time_dt = datetime.strptime(end_dt, "%Y-%m-%d")
            if start_time_dt >= end_time_dt:
                raise ValueError("Start date must be before end date")
            period_days = (end_time_dt - start_time_dt).days
            return start_dt, end_dt, period_days
        except ValueError as e:
            logging.error(f"Date parsing error: {e}. Falling back to BACKTEST_DAYS.")
    period_days = config.BACKTEST_DAYS
    start_dt = (datetime.now() - timedelta(days=period_days)).strftime("%Y-%m-%d")
    end_dt = today
    return start_dt, end_dt, period_days

def parse_screening_dates(days_back: int = 90):
    end_time = datetime.now().strftime("%Y-%m-%d")
    start_time = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    return start_time, end_time
