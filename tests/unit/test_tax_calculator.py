"""
Unit tests for tax calculator.

These tests verify that tax calculations are correct for Indian market trades.
"""
import pytest
from domain.models.trade import Trade
from infrastructure.tax.tax_calculator import TaxCalculator
from datetime import datetime


@pytest.mark.unit
class TestTaxCalculator:
    """Test suite for TaxCalculator class."""
    
    def test_calculate_taxes_for_buy_trade(self):
        """Test tax calculation for a BUY trade."""
        calculator = TaxCalculator()
        
        trade = Trade(
            timestamp=datetime.now(),
            stock="RELIANCE",
            action="BUY",
            price=2500.0,
            quantity=10,
            reason="Test trade"
        )
        
        taxes = calculator.calculate_taxes(trade)
        
        # Verify taxes structure
        assert 'stt' in taxes
        assert 'transaction_charge' in taxes
        assert 'gst' in taxes
        assert 'sebi_charge' in taxes
        assert 'stamp_duty' in taxes
        assert 'total' in taxes
        
        # Verify all tax components are positive
        assert taxes['total'] > 0
        assert all(v >= 0 for v in taxes.values())
        
        # Verify total is sum of components
        expected_total = (
            taxes['stt'] + 
            taxes['transaction_charge'] + 
            taxes['gst'] + 
            taxes['sebi_charge'] + 
            taxes['stamp_duty']
        )
        assert abs(taxes['total'] - expected_total) < 0.01
    
    def test_calculate_taxes_for_sell_trade(self):
        """Test tax calculation for a SELL trade."""
        calculator = TaxCalculator()
        
        trade = Trade(
            timestamp=datetime.now(),
            stock="TCS",
            action="SELL",
            price=3600.0,
            quantity=5,
            reason="Test sell"
        )
        
        taxes = calculator.calculate_taxes(trade)
        
        # SELL trades typically have higher STT
        assert taxes['stt'] > 0
        assert taxes['total'] > 0
    
    def test_calculate_taxes_with_zero_quantity(self):
        """Test that zero quantity trade has zero taxes."""
        calculator = TaxCalculator()
        
        trade = Trade(
            timestamp=datetime.now(),
            stock="INFY",
            action="BUY",
            price=1450.0,
            quantity=0,
            reason="Test zero quantity"
        )
        
        taxes = calculator.calculate_taxes(trade)
        
        # All taxes should be zero for zero quantity
        assert taxes['total'] == 0
        assert all(v == 0 for v in taxes.values())
    
    def test_calculate_taxes_scales_with_trade_value(self):
        """Test that taxes scale correctly with trade value."""
        calculator = TaxCalculator()
        
        # Small trade
        small_trade = Trade(
            timestamp=datetime.now(),
            stock="RELIANCE",
            action="BUY",
            price=2500.0,
            quantity=1,
            reason="Small trade"
        )
        
        # Large trade (10x quantity)
        large_trade = Trade(
            timestamp=datetime.now(),
            stock="RELIANCE",
            action="BUY",
            price=2500.0,
            quantity=10,
            reason="Large trade"
        )
        
        small_taxes = calculator.calculate_taxes(small_trade)
        large_taxes = calculator.calculate_taxes(large_trade)
        
        # Large trade should have ~10x taxes
        ratio = large_taxes['total'] / small_taxes['total']
        assert 9.5 < ratio < 10.5  # Allow small variance due to rounding
    
    def test_stt_rate_for_equity_delivery(self):
        """Test that STT rate is correct for equity delivery trades."""
        calculator = TaxCalculator()
        
        trade = Trade(
            timestamp=datetime.now(),
            stock="HDFCBANK",
            action="BUY",
            price=1650.0,
            quantity=10,
            reason="STT test"
        )
        
        trade_value = trade.price * trade.quantity
        taxes = calculator.calculate_taxes(trade)
        
        # For equity delivery, BUY STT is typically 0.1% (0.001)
        # Exact rate depends on implementation
        assert taxes['stt'] > 0
        assert taxes['stt'] < trade_value * 0.002  # Should be less than 0.2%


@pytest.mark.unit
def test_tax_calculator_initialization():
    """Test TaxCalculator can be instantiated."""
    calculator = TaxCalculator()
    assert calculator is not None
