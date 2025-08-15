"""Tests for Risk Manager V2"""

import pytest
from unittest.mock import Mock, MagicMock
import sys
import os
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from risk_manager_v2 import RiskManagerV2, RiskProfile, Position


class TestRiskManagerV2:
    """Test Risk Manager V2 functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.risk_profile = RiskProfile(
            max_position_size=1000.0,
            max_leverage=2.0,
            max_positions=3,
            risk_per_trade=0.02
        )
        self.risk_manager = RiskManagerV2(
            account_balance=10000.0,
            risk_profile=self.risk_profile
        )
    
    def test_initialization(self):
        """Test risk manager initialization"""
        assert self.risk_manager.account_balance == 10000.0
        assert self.risk_manager.initial_balance == 10000.0
        assert self.risk_manager.risk_profile.max_positions == 3
        assert len(self.risk_manager.positions) == 0
    
    def test_position_size_calculation(self):
        """Test position size calculation"""
        result = self.risk_manager.calculate_position_size(
            symbol="BTCUSDT",
            entry_price=50000.0,
            stop_loss=49000.0
        )
        
        assert "position_size" in result
        assert result["position_size"] >= 0
        assert "risk_amount" in result
        assert result["risk_amount"] == 200.0  # 2% of 10000
    
    def test_stop_loss_calculation(self):
        """Test stop loss calculation"""
        stop_loss = self.risk_manager.calculate_stop_loss(
            symbol="BTCUSDT",
            entry_price=50000.0,
            side="long",
            atr=500.0
        )
        
        # With ATR multiplier of 2.0
        expected_stop = 50000.0 - (500.0 * 2.0)
        assert stop_loss == expected_stop
    
    def test_take_profit_calculation(self):
        """Test take profit calculation"""
        take_profit = self.risk_manager.calculate_take_profit(
            entry_price=50000.0,
            stop_loss=49000.0,
            side="long"
        )
        
        # With risk/reward ratio of 2.0
        risk = 1000.0
        expected_tp = 50000.0 + (risk * 2.0)
        assert take_profit == expected_tp
    
    def test_add_position(self):
        """Test adding a position"""
        position = Position(
            symbol="BTCUSDT",
            side="long",
            entry_price=50000.0,
            current_price=50000.0,
            quantity=0.1
        )
        
        self.risk_manager.add_position(position)
        
        assert "BTCUSDT" in self.risk_manager.positions
        assert self.risk_manager.positions["BTCUSDT"] == position
        assert self.risk_manager.metrics["total_trades"] == 1
    
    def test_close_position(self):
        """Test closing a position"""
        # Add a position first
        position = Position(
            symbol="BTCUSDT",
            side="long",
            entry_price=50000.0,
            current_price=50000.0,
            quantity=0.1
        )
        self.risk_manager.add_position(position)
        
        # Close with profit
        self.risk_manager.close_position("BTCUSDT", exit_price=51000.0)
        
        # Check position is closed
        assert "BTCUSDT" not in self.risk_manager.positions
        assert self.risk_manager.metrics["winning_trades"] == 1
        assert self.risk_manager.account_balance > 10000.0
    
    def test_trailing_stop_activation(self):
        """Test trailing stop activation"""
        position = Position(
            symbol="BTCUSDT",
            side="long",
            entry_price=50000.0,
            current_price=50000.0,
            quantity=0.1
        )
        
        # Price increases by 1% (activation threshold)
        new_stop = self.risk_manager.update_trailing_stop(position, 50500.0)
        
        assert position.trailing_activated == True
        assert position.trailing_stop > 0
        assert new_stop is not None
    
    def test_risk_limits_check(self):
        """Test risk limit checking"""
        # Add maximum positions
        for i in range(3):
            position = Position(
                symbol=f"SYMBOL{i}",
                side="long",
                entry_price=100.0,
                current_price=100.0,
                quantity=1.0
            )
            self.risk_manager.add_position(position)
        
        # Check limits
        checks = self.risk_manager.check_risk_limits()
        
        assert checks["passed"] == False
        assert len(checks["errors"]) > 0
        assert "Maximum positions reached" in checks["errors"][0]
    
    def test_position_pnl_calculation(self):
        """Test P&L calculation for positions"""
        position = Position(
            symbol="BTCUSDT",
            side="long",
            entry_price=50000.0,
            current_price=51000.0,
            quantity=0.1
        )
        
        pnl = position.calculate_pnl()
        
        # Long position with 1000 price increase
        expected_pnl = (51000.0 - 50000.0) * 0.1
        assert pnl == expected_pnl
        assert position.unrealized_pnl == expected_pnl
    
    def test_var_calculation(self):
        """Test Value at Risk calculation"""
        # Add some return history
        for i in range(100):
            self.risk_manager.returns_history.append(0.01 * (i % 3 - 1))
        
        var = self.risk_manager.calculate_var(confidence_level=0.95)
        
        assert var >= 0
        assert self.risk_manager.metrics["var_daily"] == var