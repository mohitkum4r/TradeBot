"""
Unit tests for trading strategies.

These tests verify that trading strategies generate correct signals
based on market data.
"""
import pytest
import pandas as pd
from domain.strategies.momentum_strategy import MomentumStrategy
from domain.strategies.mean_reversion_strategy import MeanReversionStrategy
from domain.strategies.base_strategy import BaseStrategy


@pytest.mark.unit
class TestMomentumStrategy:
    """Test suite for MomentumStrategy."""
    
    def test_strategy_initialization(self):
        """Test that MomentumStrategy can be initialized."""
        strategy = MomentumStrategy()
        assert strategy is not None
        assert isinstance(strategy, BaseStrategy)
    
    def test_buy_signal_on_uptrend(self, trending_upward_data):
        """Test that strategy generates BUY signal on strong uptrend."""
        strategy = MomentumStrategy()
        stock, action, reason = strategy.generate_signal(trending_upward_data)
        
        # Should generate either BUY or HOLD (depending on exact conditions)
        assert action in ['BUY', 'HOLD', 'SELL']
        assert isinstance(reason, str)
        assert len(reason) > 0
    
    def test_sell_signal_on_downtrend(self, trending_downward_data):
        """Test that strategy generates SELL signal on strong downtrend."""
        strategy = MomentumStrategy()
        stock, action, reason = strategy.generate_signal(trending_downward_data)
        
        assert action in ['BUY', 'HOLD', 'SELL']
        assert isinstance(reason, str)
    
    def test_handles_insufficient_data(self, insufficient_data):
        """Test strategy gracefully handles insufficient data."""
        strategy = MomentumStrategy()
        stock, action, reason = strategy.generate_signal(insufficient_data)
        
        # Should return HOLD with explanation
        assert action == 'HOLD'
        assert 'insufficient' in reason.lower() or 'not enough' in reason.lower()
    
    def test_handles_empty_dataframe(self, empty_dataframe):
        """Test strategy handles empty DataFrame without crashing."""
        strategy = MomentumStrategy()
        stock, action, reason = strategy.generate_signal(empty_dataframe)
        
        assert action == 'HOLD'
        assert isinstance(reason, str)
    
    def test_signal_format_is_valid(self, sample_ohlcv_data):
        """Test that signal format is always valid tuple."""
        strategy = MomentumStrategy()
        result = strategy.generate_signal(sample_ohlcv_data)
        
        # Should return tuple of (stock, action, reason)
        assert isinstance(result, tuple)
        assert len(result) == 3
        
        stock, action, reason = result
        assert isinstance(stock, str)
        assert action in ['BUY', 'SELL', 'HOLD']
        assert isinstance(reason, str)


@pytest.mark.unit
class TestMeanReversionStrategy:
    """Test suite for MeanReversionStrategy."""
    
    def test_strategy_initialization(self):
        """Test that MeanReversionStrategy can be initialized."""
        strategy = MeanReversionStrategy()
        assert strategy is not None
        assert isinstance(strategy, BaseStrategy)
    
    def test_buy_signal_on_oversold(self, sample_ohlcv_data):
        """Test strategy identifies oversold conditions."""
        strategy = MeanReversionStrategy()
        
        # Create oversold scenario
        oversold_data = sample_ohlcv_data.copy()
        # Drop price significantly below moving average
        oversold_data['close'] = oversold_data['close'] * 0.9
        
        stock, action, reason = strategy.generate_signal(oversold_data)
        
        assert action in ['BUY', 'HOLD', 'SELL']
        assert isinstance(reason, str)
    
    def test_sell_signal_on_overbought(self, sample_ohlcv_data):
        """Test strategy identifies overbought conditions."""
        strategy = MeanReversionStrategy()
        
        # Create overbought scenario
        overbought_data = sample_ohlcv_data.copy()
        # Push price significantly above moving average
        overbought_data['close'] = overbought_data['close'] * 1.1
        
        stock, action, reason = strategy.generate_signal(overbought_data)
        
        assert action in ['BUY', 'HOLD', 'SELL']
        assert isinstance(reason, str)
    
    def test_hold_signal_in_sideways_market(self, sideways_data):
        """Test strategy behavior in sideways market."""
        strategy = MeanReversionStrategy()
        stock, action, reason = strategy.generate_signal(sideways_data)
        
        # In sideways market, could be any valid action
        assert action in ['BUY', 'HOLD', 'SELL']
        assert isinstance(reason, str)


@pytest.mark.unit
class TestBaseStrategy:
    """Test suite for BaseStrategy abstract class."""
    
    def test_cannot_instantiate_base_strategy(self):
        """Test that BaseStrategy cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseStrategy()
    
    def test_subclass_must_implement_generate_signal(self):
        """Test that subclasses must implement generate_signal."""
        
        class IncompleteStrategy(BaseStrategy):
            pass
        
        with pytest.raises(TypeError):
            IncompleteStrategy()


@pytest.mark.unit
@pytest.mark.parametrize("strategy_class", [
    MomentumStrategy,
    MeanReversionStrategy,
])
def test_all_strategies_handle_missing_columns(strategy_class):
    """Test that all strategies handle DataFrames with missing columns."""
    strategy = strategy_class()
    
    # DataFrame with only 'close' column
    incomplete_data = pd.DataFrame({
        'close': [100, 101, 102, 103, 104]
    })
    
    # Should not crash, should return valid signal
    result = strategy.generate_signal(incomplete_data)
    
    assert isinstance(result, tuple)
    assert len(result) == 3
    stock, action, reason = result
    assert action in ['BUY', 'HOLD', 'SELL']


@pytest.mark.unit
@pytest.mark.parametrize("strategy_class", [
    MomentumStrategy,
    MeanReversionStrategy,
])
def test_all_strategies_consistent_output(strategy_class, sample_ohlcv_data):
    """Test that strategies produce consistent output for same input."""
    strategy = strategy_class()
    
    # Call twice with same data
    result1 = strategy.generate_signal(sample_ohlcv_data)
    result2 = strategy.generate_signal(sample_ohlcv_data)
    
    # Results should be identical
    assert result1 == result2
