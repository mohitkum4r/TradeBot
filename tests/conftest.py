"""
Pytest configuration and shared fixtures for TradeBot tests.

This file provides common fixtures and configuration for all tests.
"""
import pytest
import pandas as pd
from datetime import datetime, timedelta
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import Config
from domain.models.models import Base


@pytest.fixture
def sample_ohlcv_data() -> pd.DataFrame:
    """
    Provide sample OHLCV data for testing strategies.
    
    Returns:
        DataFrame with 100 rows of sample stock data
    """
    dates = pd.date_range(end=datetime.now(), periods=100, freq='1h')
    return pd.DataFrame({
        'open': range(100, 200),
        'high': range(105, 205),
        'low': range(95, 195),
        'close': range(100, 200),
        'volume': [1000000 + i * 1000 for i in range(100)]
    }, index=dates)


@pytest.fixture
def empty_dataframe() -> pd.DataFrame:
    """Provide an empty DataFrame for edge case testing."""
    return pd.DataFrame()


@pytest.fixture
def insufficient_data() -> pd.DataFrame:
    """Provide DataFrame with insufficient data for strategy calculations."""
    return pd.DataFrame({
        'open': [100, 101],
        'high': [105, 106],
        'low': [95, 96],
        'close': [100, 101],
        'volume': [1000000, 1100000]
    })


@pytest.fixture
def test_db_session() -> Generator[Session, None, None]:
    """
    Provide a test database session using in-memory SQLite.
    
    The database is created fresh for each test and torn down after.
    
    Yields:
        SQLAlchemy Session for testing
    """
    # Create in-memory SQLite database
    engine = create_engine('sqlite:///:memory:', echo=False)
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create session
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def mock_config() -> Config:
    """
    Provide a mock Config object for testing.
    
    Returns:
        Config instance with test values
    """
    config = Config()
    config.MODE = "PAPER"
    config.INITIAL_CAPITAL = 100000.0
    config.MAX_EXPOSURE_PER_TRADE = 0.2
    config.RISK_PER_TRADE = 0.01
    config.STOP_LOSS_PCT = 0.05
    config.TAKE_PROFIT_PCT = 0.10
    return config


@pytest.fixture
def sample_stock_symbols() -> list[str]:
    """Provide list of sample stock symbols for testing."""
    return ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]


@pytest.fixture
def mock_ltp_data() -> dict[str, float]:
    """
    Provide mock Last Traded Price data for stocks.
    
    Returns:
        Dictionary mapping stock symbols to prices
    """
    return {
        "RELIANCE": 2500.50,
        "TCS": 3600.75,
        "INFY": 1450.25,
        "HDFCBANK": 1650.00,
        "ICICIBANK": 980.50
    }


@pytest.fixture
def trending_upward_data() -> pd.DataFrame:
    """
    Provide data showing clear upward trend.
    
    Useful for testing momentum strategies.
    """
    dates = pd.date_range(end=datetime.now(), periods=50, freq='1h')
    close_prices = [1000 + i * 10 for i in range(50)]  # Steady upward trend
    return pd.DataFrame({
        'open': [p - 5 for p in close_prices],
        'high': [p + 10 for p in close_prices],
        'low': [p - 10 for p in close_prices],
        'close': close_prices,
        'volume': [1000000] * 50
    }, index=dates)


@pytest.fixture
def trending_downward_data() -> pd.DataFrame:
    """
    Provide data showing clear downward trend.
    
    Useful for testing sell signals and stop loss.
    """
    dates = pd.date_range(end=datetime.now(), periods=50, freq='1h')
    close_prices = [2000 - i * 10 for i in range(50)]  # Steady downward trend
    return pd.DataFrame({
        'open': [p + 5 for p in close_prices],
        'high': [p + 10 for p in close_prices],
        'low': [p - 10 for p in close_prices],
        'close': close_prices,
        'volume': [1000000] * 50
    }, index=dates)


@pytest.fixture
def sideways_data() -> pd.DataFrame:
    """
    Provide data showing sideways/ranging market.
    
    Useful for testing mean reversion strategies.
    """
    dates = pd.date_range(end=datetime.now(), periods=50, freq='1h')
    # Price oscillates around 1500
    close_prices = [1500 + (i % 10 - 5) * 5 for i in range(50)]
    return pd.DataFrame({
        'open': [p - 2 for p in close_prices],
        'high': [p + 5 for p in close_prices],
        'low': [p - 5 for p in close_prices],
        'close': close_prices,
        'volume': [1000000] * 50
    }, index=dates)


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
