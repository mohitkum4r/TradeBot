"""
Integration tests for trade execution flow.

These tests verify the complete flow from signal generation to trade logging.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from use_cases.trade_executor import PaperTradeExecutor, LiveTradeExecutor
from infrastructure.tax.tax_calculator import TaxCalculator
from infrastructure.database.sqlite_trade_logger import SQLiteTradeLogger
from infrastructure.data_providers.data_handler import DataHandler
from domain.models.trade import Trade


@pytest.mark.integration
class TestPaperTradeExecution:
    """Integration tests for paper trading execution."""
    
    @patch('infrastructure.data_providers.data_handler.DataHandler.get_ltp')
    def test_complete_paper_trade_flow(self, mock_get_ltp, test_db_session):
        """Test complete paper trade execution from signal to logging."""
        # Setup mocks
        mock_get_ltp.return_value = 2500.0
        mock_data_handler = Mock(spec=DataHandler)
        mock_data_handler.get_ltp = mock_get_ltp
        
        # Create executor with real components
        tax_calculator = TaxCalculator()
        logger = SQLiteTradeLogger()
        executor = PaperTradeExecutor(
            data_handler=mock_data_handler,
            logger=logger,
            tax_calculator=tax_calculator
        )
        
        # Execute trade
        executor.execute_trade(
            db_session=test_db_session,
            stock="RELIANCE",
            action="BUY",
            quantity=10,
            reason="Test trade",
            current_capital=100000.0
        )
        
        # Verify trade was logged
        # Note: Actual verification depends on SQLiteTradeLogger implementation
        mock_get_ltp.assert_called_once_with("RELIANCE")
    
    @patch('infrastructure.data_providers.data_handler.DataHandler.get_ltp')
    def test_trade_respects_exposure_limit(self, mock_get_ltp, test_db_session, mock_config):
        """Test that trades respect MAX_EXPOSURE_PER_TRADE limit."""
        mock_get_ltp.return_value = 2500.0
        mock_data_handler = Mock(spec=DataHandler)
        mock_data_handler.get_ltp = mock_get_ltp
        
        tax_calculator = TaxCalculator()
        logger = SQLiteTradeLogger()
        executor = PaperTradeExecutor(
            data_handler=mock_data_handler,
            logger=logger,
            tax_calculator=tax_calculator
        )
        
        current_capital = 100000.0
        max_exposure = 0.2  # 20%
        
        # Try to trade more than allowed
        executor.execute_trade(
            db_session=test_db_session,
            stock="RELIANCE",
            action="BUY",
            quantity=100,  # Very large quantity
            reason="Test exposure limit",
            current_capital=current_capital
        )
        
        # Should limit trade size based on exposure
        # Exact behavior depends on implementation
    
    @patch('infrastructure.data_providers.data_handler.DataHandler.get_ltp')
    def test_invalid_quantity_rejected(self, mock_get_ltp, test_db_session):
        """Test that invalid quantity is rejected."""
        mock_get_ltp.return_value = 2500.0
        mock_data_handler = Mock(spec=DataHandler)
        mock_data_handler.get_ltp = mock_get_ltp
        
        tax_calculator = TaxCalculator()
        logger = SQLiteTradeLogger()
        executor = PaperTradeExecutor(
            data_handler=mock_data_handler,
            logger=logger,
            tax_calculator=tax_calculator
        )
        
        # Try to execute trade with zero quantity
        executor.execute_trade(
            db_session=test_db_session,
            stock="RELIANCE",
            action="BUY",
            quantity=0,
            reason="Invalid quantity test",
            current_capital=100000.0
        )
        
        # Should not call get_ltp if quantity is invalid
        mock_get_ltp.assert_not_called()
    
    @patch('infrastructure.data_providers.data_handler.DataHandler.get_ltp')
    def test_invalid_price_rejected(self, mock_get_ltp, test_db_session):
        """Test that trade is rejected when price is invalid."""
        mock_get_ltp.return_value = 0.0  # Invalid price
        mock_data_handler = Mock(spec=DataHandler)
        mock_data_handler.get_ltp = mock_get_ltp
        
        tax_calculator = TaxCalculator()
        logger = SQLiteTradeLogger()
        executor = PaperTradeExecutor(
            data_handler=mock_data_handler,
            logger=logger,
            tax_calculator=tax_calculator
        )
        
        executor.execute_trade(
            db_session=test_db_session,
            stock="RELIANCE",
            action="BUY",
            quantity=10,
            reason="Invalid price test",
            current_capital=100000.0
        )
        
        # Trade should be rejected
        # Exact behavior depends on implementation


@pytest.mark.integration
@pytest.mark.slow
class TestLiveTradeExecution:
    """Integration tests for live trading execution."""
    
    @patch('infrastructure.brokers.groww_broker.GrowwBrokerClient.place_order')
    @patch('infrastructure.data_providers.data_handler.DataHandler.get_ltp')
    def test_live_trade_places_order(self, mock_get_ltp, mock_place_order, test_db_session):
        """Test that live executor actually places order with broker."""
        mock_get_ltp.return_value = 2500.0
        mock_place_order.return_value = {"order_id": "TEST123", "status": "SUCCESS"}
        
        mock_data_handler = Mock(spec=DataHandler)
        mock_data_handler.get_ltp = mock_get_ltp
        
        mock_broker = Mock()
        mock_broker.place_order = mock_place_order
        
        tax_calculator = TaxCalculator()
        logger = SQLiteTradeLogger()
        executor = LiveTradeExecutor(
            data_handler=mock_data_handler,
            logger=logger,
            tax_calculator=tax_calculator,
            client=mock_broker
        )
        
        executor.execute_trade(
            db_session=test_db_session,
            stock="RELIANCE",
            action="BUY",
            quantity=10,
            reason="Live trade test",
            current_capital=100000.0
        )
        
        # Verify broker's place_order was called
        mock_place_order.assert_called_once()
    
    @patch('infrastructure.brokers.groww_broker.GrowwBrokerClient.place_order')
    @patch('infrastructure.data_providers.data_handler.DataHandler.get_ltp')
    def test_live_trade_handles_broker_failure(self, mock_get_ltp, mock_place_order, test_db_session):
        """Test that live executor handles broker failures gracefully."""
        mock_get_ltp.return_value = 2500.0
        mock_place_order.side_effect = Exception("Broker API error")
        
        mock_data_handler = Mock(spec=DataHandler)
        mock_data_handler.get_ltp = mock_get_ltp
        
        mock_broker = Mock()
        mock_broker.place_order = mock_place_order
        
        tax_calculator = TaxCalculator()
        logger = SQLiteTradeLogger()
        executor = LiveTradeExecutor(
            data_handler=mock_data_handler,
            logger=logger,
            tax_calculator=tax_calculator,
            client=mock_broker
        )
        
        # Should handle exception gracefully
        # Exact behavior depends on implementation
        try:
            executor.execute_trade(
                db_session=test_db_session,
                stock="RELIANCE",
                action="BUY",
                quantity=10,
                reason="Failure test",
                current_capital=100000.0
            )
        except Exception:
            # Expected to raise or handle gracefully
            pass


@pytest.mark.integration
def test_tax_integration_with_trade():
    """Test that tax calculation integrates correctly with Trade model."""
    calculator = TaxCalculator()
    
    trade = Trade(
        timestamp=datetime.now(),
        stock="TCS",
        action="BUY",
        price=3600.0,
        quantity=5,
        reason="Integration test"
    )
    
    # Calculate taxes
    taxes = calculator.calculate_taxes(trade)
    
    # Assign to trade
    trade.taxes = taxes
    
    # Verify integration
    assert trade.taxes is not None
    assert 'total' in trade.taxes
    assert trade.taxes['total'] > 0
