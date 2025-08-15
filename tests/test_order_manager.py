"""Tests for Order Manager"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
import os
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from order_manager import OrderManager, Order, OrderType, OrderSide, OrderStatus, TimeInForce


class TestOrderManager:
    """Test Order Manager functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.mock_client = Mock()
        self.mock_risk_manager = Mock()
        self.order_manager = OrderManager(
            bybit_client=self.mock_client,
            risk_manager=self.mock_risk_manager
        )
    
    def test_initialization(self):
        """Test order manager initialization"""
        assert self.order_manager.client == self.mock_client
        assert self.order_manager.risk_manager == self.mock_risk_manager
        assert len(self.order_manager.orders) == 0
        assert len(self.order_manager.active_orders) == 0
    
    def test_create_order(self):
        """Test order creation"""
        # Mock risk manager approval
        self.mock_risk_manager.check_order_risk.return_value = {
            "approved": True
        }
        
        order = self.order_manager.create_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.1,
            price=50000.0
        )
        
        assert order.symbol == "BTCUSDT"
        assert order.side == OrderSide.BUY
        assert order.quantity == 0.1
        assert order.price == 50000.0
        assert order.status != OrderStatus.REJECTED
        assert order.order_id in self.order_manager.orders
    
    def test_order_validation(self):
        """Test order validation"""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.1,
            price=50000.0
        )
        
        result = self.order_manager.validate_order(order)
        
        assert result["valid"] == True
        assert "reason" in result
    
    def test_order_validation_failure(self):
        """Test order validation with invalid parameters"""
        # Order with zero quantity
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0,
            price=50000.0
        )
        
        result = self.order_manager.validate_order(order)
        
        assert result["valid"] == False
        assert "Quantity must be positive" in result["reason"]
    
    def test_submit_order(self):
        """Test order submission to exchange"""
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.1,
            price=50000.0,
            status=OrderStatus.PENDING
        )
        
        # Mock successful API response
        self.mock_client.session.place_order.return_value = {
            "retCode": 0,
            "result": {
                "orderId": "exchange123"
            }
        }
        
        success = self.order_manager.submit_order(order)
        
        assert success == True
        assert order.exchange_order_id == "exchange123"
        assert order.status == OrderStatus.NEW
    
    def test_cancel_order(self):
        """Test order cancellation"""
        # Create and store an order
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.1,
            price=50000.0,
            status=OrderStatus.NEW,
            exchange_order_id="exchange123"
        )
        self.order_manager.orders[order.order_id] = order
        self.order_manager.active_orders["BTCUSDT"] = [order]
        
        # Mock successful cancellation
        self.mock_client.session.cancel_order.return_value = {
            "retCode": 0
        }
        
        success = self.order_manager.cancel_order(order.order_id)
        
        assert success == True
        assert order.status == OrderStatus.CANCELLED
        assert "BTCUSDT" not in self.order_manager.active_orders or \
               order not in self.order_manager.active_orders["BTCUSDT"]
    
    def test_process_fill(self):
        """Test order fill processing"""
        # Create an order
        order = Order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.1,
            price=50000.0,
            status=OrderStatus.NEW
        )
        self.order_manager.orders[order.order_id] = order
        self.order_manager.active_orders["BTCUSDT"] = [order]
        
        # Process partial fill
        fill = {
            "qty": 0.05,
            "price": 50000.0,
            "commission": 0.0001
        }
        
        self.order_manager.process_fill(order.order_id, fill)
        
        assert order.filled_quantity == 0.05
        assert order.remaining_quantity == 0.05
        assert order.average_fill_price == 50000.0
        assert order.status == OrderStatus.PARTIALLY_FILLED
        
        # Process complete fill
        fill2 = {
            "qty": 0.05,
            "price": 50000.0,
            "commission": 0.0001
        }
        
        self.order_manager.process_fill(order.order_id, fill2)
        
        assert order.filled_quantity == 0.1
        assert order.remaining_quantity == 0
        assert order.status == OrderStatus.FILLED
        assert order.order_id not in self.order_manager.active_orders.get("BTCUSDT", [])
    
    def test_smart_routing(self):
        """Test smart order routing"""
        self.order_manager.smart_routing["enabled"] = True
        self.order_manager.smart_routing["use_iceberg"] = True
        self.order_manager.routing_rules["max_order_size"]["BTCUSDT"] = 1.0
        
        # Mock risk manager approval
        self.mock_risk_manager.check_order_risk.return_value = {
            "approved": True
        }
        
        # Create large order
        order = self.order_manager.create_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.6,  # > 50% of max size
            price=50000.0
        )
        
        # Check iceberg was applied
        assert "iceberg" in order.metadata
        assert order.metadata["iceberg"] == True
    
    def test_get_metrics(self):
        """Test metrics calculation"""
        # Add some completed orders
        for i in range(5):
            order = Order(
                symbol="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=0.1,
                price=50000.0
            )
            self.order_manager.orders[order.order_id] = order
            self.order_manager.metrics["total_orders"] += 1
            if i < 3:
                self.order_manager.metrics["filled_orders"] += 1
        
        metrics = self.order_manager.get_metrics()
        
        assert metrics["total_orders"] == 5
        assert metrics["filled_orders"] == 3
        assert metrics["fill_rate"] == 0.6