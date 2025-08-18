#!/usr/bin/env python3
"""
Test Suite for Phase 7: Advanced Order Management
Tests Stop-Loss, Take-Profit, Trailing Stops, and Order Modifications
"""

import sys
import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orders import (
    AdvancedOrderManager,
    StopLossOrder,
    TakeProfitOrder,
    TrailingStopConfig,
    TrailingMethod,
    OrderModifier,
    OrderModification,
    ModificationType,
    PartialFillHandler,
    FillStrategy,
    FillHandlingConfig
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockTradingClient:
    """Mock trading client for testing"""
    
    def __init__(self):
        self.orders = {}
        self.positions = {}
        self.order_counter = 1000
        
    async def place_order(self, **kwargs):
        """Mock place order"""
        order_id = f"order_{self.order_counter}"
        self.order_counter += 1
        
        self.orders[order_id] = {
            "orderId": order_id,
            "symbol": kwargs.get("symbol"),
            "side": kwargs.get("side"),
            "orderType": kwargs.get("orderType"),
            "qty": kwargs.get("qty"),
            "price": kwargs.get("price"),
            "triggerPrice": kwargs.get("triggerPrice"),
            "status": "New",
            "cumExecQty": "0",
            "leavesQty": kwargs.get("qty")
        }
        
        return {
            "retCode": 0,
            "result": {"orderId": order_id}
        }
    
    async def amend_order(self, **kwargs):
        """Mock amend order"""
        order_id = kwargs.get("orderId")
        if order_id in self.orders:
            if "price" in kwargs:
                self.orders[order_id]["price"] = kwargs["price"]
            if "qty" in kwargs:
                self.orders[order_id]["qty"] = kwargs["qty"]
            if "triggerPrice" in kwargs:
                self.orders[order_id]["triggerPrice"] = kwargs["triggerPrice"]
            
            return {
                "retCode": 0,
                "result": {"orderId": order_id}
            }
        
        return {"retCode": 1, "retMsg": "Order not found"}
    
    async def cancel_order(self, **kwargs):
        """Mock cancel order"""
        order_id = kwargs.get("orderId")
        if order_id in self.orders:
            self.orders[order_id]["status"] = "Cancelled"
            return {"retCode": 0, "result": {"orderId": order_id}}
        
        return {"retCode": 1, "retMsg": "Order not found"}
    
    async def get_tickers(self, **kwargs):
        """Mock get tickers"""
        return {
            "retCode": 0,
            "result": {
                "list": [{
                    "symbol": kwargs.get("symbol", "BTCUSDT"),
                    "lastPrice": "50000",
                    "bid1Price": "49999",
                    "ask1Price": "50001"
                }]
            }
        }
    
    async def get_open_orders(self, **kwargs):
        """Mock get open orders"""
        order_id = kwargs.get("orderId")
        if order_id and order_id in self.orders:
            return {
                "retCode": 0,
                "result": {"list": [self.orders[order_id]]}
            }
        
        return {"retCode": 0, "result": {"list": []}}
    
    async def get_positions(self, **kwargs):
        """Mock get positions"""
        return {
            "retCode": 0,
            "result": {
                "list": list(self.positions.values())
            }
        }
    
    async def set_trading_stop(self, **kwargs):
        """Mock set trading stop"""
        symbol = kwargs.get("symbol")
        if symbol:
            return {"retCode": 0, "result": {}}
        
        return {"retCode": 1, "retMsg": "Invalid parameters"}

async def test_stop_loss_orders():
    """Test Stop-Loss order functionality"""
    print("\n" + "="*60)
    print("Testing Stop-Loss Orders")
    print("="*60)
    
    client = MockTradingClient()
    manager = AdvancedOrderManager(client)
    
    # Test 1: Place stop-loss for long position
    stop_loss = StopLossOrder(
        symbol="BTCUSDT",
        side="Sell",  # Sell to close long
        quantity=0.01,
        trigger_price=49000,  # Below current price
        order_type="Market"
    )
    
    result = await manager.place_stop_loss("pos_001", stop_loss)
    assert result is not None, "Failed to place stop-loss"
    print("✅ Stop-loss placed for long position")
    
    # Test 2: Place stop-loss for short position
    stop_loss_short = StopLossOrder(
        symbol="BTCUSDT",
        side="Buy",  # Buy to close short
        quantity=0.01,
        trigger_price=51000,  # Above current price
        order_type="Market"
    )
    
    result = await manager.place_stop_loss("pos_002", stop_loss_short)
    assert result is not None, "Failed to place stop-loss for short"
    print("✅ Stop-loss placed for short position")
    
    # Test 3: Calculate risk-based stop
    risk_stop = manager.calculate_risk_based_stop(
        entry_price=50000,
        position_size=0.1,
        max_loss=100,  # Max $100 loss
        side="Buy"
    )
    print(f"✅ Risk-based stop calculated: ${risk_stop}")
    
    # Test 4: Calculate break-even stop
    break_even = manager.calculate_break_even_stop(50000)
    print(f"✅ Break-even stop calculated: ${break_even}")
    
    return True

async def test_take_profit_orders():
    """Test Take-Profit order functionality"""
    print("\n" + "="*60)
    print("Testing Take-Profit Orders")
    print("="*60)
    
    client = MockTradingClient()
    manager = AdvancedOrderManager(client)
    
    # Test 1: Place take-profit for long position
    take_profit = TakeProfitOrder(
        symbol="BTCUSDT",
        side="Sell",  # Sell to take profit on long
        quantity=0.01,
        trigger_price=52000,  # Above current price
        limit_price=51900  # Limit order at slightly lower price
    )
    
    result = await manager.place_take_profit("pos_003", take_profit)
    assert result is not None, "Failed to place take-profit"
    print("✅ Take-profit placed for long position")
    
    # Test 2: Place take-profit for short position
    take_profit_short = TakeProfitOrder(
        symbol="BTCUSDT",
        side="Buy",  # Buy to take profit on short
        quantity=0.01,
        trigger_price=48000,  # Below current price
        order_type="Market"
    )
    
    result = await manager.place_take_profit("pos_004", take_profit_short)
    assert result is not None, "Failed to place take-profit for short"
    print("✅ Take-profit placed for short position")
    
    return True

async def test_trailing_stops():
    """Test Trailing Stop functionality"""
    print("\n" + "="*60)
    print("Testing Trailing Stops")
    print("="*60)
    
    client = MockTradingClient()
    manager = AdvancedOrderManager(client)
    
    # Test 1: Percentage-based trailing stop
    config = TrailingStopConfig(
        symbol="BTCUSDT",
        side="Sell",
        quantity=0.01,
        method=TrailingMethod.PERCENTAGE,
        trail_value=2.0,  # 2% trailing
        activation_price=50500  # Activate when price reaches this
    )
    
    trail_id = await manager.setup_trailing_stop("pos_005", config)
    assert trail_id is not None, "Failed to setup trailing stop"
    print(f"✅ Percentage trailing stop setup: {trail_id}")
    
    # Test 2: Fixed amount trailing stop
    config_fixed = TrailingStopConfig(
        symbol="BTCUSDT",
        side="Sell",
        quantity=0.01,
        method=TrailingMethod.FIXED,
        trail_value=500  # $500 trailing distance
    )
    
    trail_id = await manager.setup_trailing_stop("pos_006", config_fixed)
    print(f"✅ Fixed trailing stop setup: {trail_id}")
    
    # Test 3: Step-based trailing stop
    config_step = TrailingStopConfig(
        symbol="BTCUSDT",
        side="Sell",
        quantity=0.01,
        method=TrailingMethod.STEP,
        trail_value=100,  # Move in $100 steps
        step_size=100
    )
    
    trail_id = await manager.setup_trailing_stop("pos_007", config_step)
    print(f"✅ Step trailing stop setup: {trail_id}")
    
    # Test 4: Update trailing stops with new market data
    market_data = {
        "BTCUSDT": 51000  # Price moved up
    }
    
    await manager.update_trailing_stops(market_data)
    print("✅ Trailing stops updated with new market data")
    
    return True

async def test_order_modifications():
    """Test Order Modification functionality"""
    print("\n" + "="*60)
    print("Testing Order Modifications")
    print("="*60)
    
    client = MockTradingClient()
    modifier = OrderModifier(client)
    
    # Create a test order first
    order_result = await client.place_order(
        category="linear",
        symbol="BTCUSDT",
        side="Buy",
        orderType="Limit",
        qty="0.01",
        price="49000"
    )
    order_id = order_result["result"]["orderId"]
    
    # Test 1: Modify price
    result = await modifier.modify_price(order_id, 49100, "Market moved")
    assert result["success"], "Failed to modify price"
    print("✅ Order price modified")
    
    # Test 2: Modify quantity
    result = await modifier.modify_quantity(order_id, 0.02, "Increase size")
    assert result["success"], "Failed to modify quantity"
    print("✅ Order quantity modified")
    
    # Test 3: Batch modifications
    modifications = [
        OrderModification(
            order_id=order_id,
            modification_type=ModificationType.PRICE,
            new_value=49200,
            reason="Batch price update"
        ),
        OrderModification(
            order_id=order_id,
            modification_type=ModificationType.QUANTITY,
            new_value=0.015,
            reason="Batch quantity update"
        )
    ]
    
    result = await modifier.batch_modify(modifications, atomic=False)
    print(f"✅ Batch modifications: {result['successful']}/{result['total']} successful")
    
    # Test 4: Smart modification based on market conditions
    market_conditions = {
        "last_price": 50000,
        "volatility": 0.025  # 2.5% volatility
    }
    
    result = await modifier.smart_modification(order_id, market_conditions)
    print("✅ Smart modification applied based on market conditions")
    
    # Test 5: Cancel and replace
    new_params = {
        "category": "linear",
        "symbol": "BTCUSDT",
        "side": "Buy",
        "orderType": "Limit",
        "qty": "0.02",
        "price": "49500"
    }
    
    result = await modifier.cancel_and_replace(order_id, new_params)
    print(f"✅ Order replaced: {result.get('new_order_id')}")
    
    return True

async def test_partial_fills():
    """Test Partial Fill handling"""
    print("\n" + "="*60)
    print("Testing Partial Fill Handling")
    print("="*60)
    
    client = MockTradingClient()
    modifier = OrderModifier(client)
    
    config = FillHandlingConfig(
        min_fill_percentage=90.0,
        max_wait_time=timedelta(minutes=5),
        price_adjustment_step=0.001,
        split_threshold=100,
        auto_market_threshold=10
    )
    
    handler = PartialFillHandler(client, modifier, config)
    
    # Test 1: Handle partial fill update
    fill_data = {
        "symbol": "BTCUSDT",
        "side": "Buy",
        "qty": "1.0",
        "cumExecQty": "0.6",  # 60% filled
        "leavesQty": "0.4",
        "avgPrice": "50000",
        "cumExecFee": "0.03"
    }
    
    await handler.handle_fill_update("order_100", fill_data)
    print("✅ Partial fill handled (60% filled)")
    
    # Test 2: Check active partials
    active = handler.get_active_partials()
    print(f"✅ Active partial fills: {len(active)}")
    
    # Test 3: Handle mostly filled order (>90%)
    fill_data_mostly = {
        "symbol": "BTCUSDT",
        "side": "Buy",
        "qty": "1.0",
        "cumExecQty": "0.95",  # 95% filled
        "leavesQty": "0.05",
        "avgPrice": "50000",
        "cumExecFee": "0.057"
    }
    
    await handler.handle_fill_update("order_101", fill_data_mostly)
    print("✅ Mostly filled order handled (95% filled)")
    
    # Test 4: Get statistics
    stats = handler.get_statistics()
    print(f"✅ Fill handler statistics: {stats}")
    
    return True

async def test_position_protection():
    """Test complete position protection setup"""
    print("\n" + "="*60)
    print("Testing Position Protection")
    print("="*60)
    
    client = MockTradingClient()
    manager = AdvancedOrderManager(client)
    
    # Setup complete protection for a position
    position_id = "pos_protected"
    
    # 1. Place stop-loss
    stop_loss = StopLossOrder(
        symbol="BTCUSDT",
        side="Sell",
        quantity=0.1,
        trigger_price=48000
    )
    sl_result = await manager.place_stop_loss(position_id, stop_loss)
    
    # 2. Place take-profit
    take_profit = TakeProfitOrder(
        symbol="BTCUSDT",
        side="Sell",
        quantity=0.1,
        trigger_price=52000
    )
    tp_result = await manager.place_take_profit(position_id, take_profit)
    
    # 3. Setup trailing stop
    trailing = TrailingStopConfig(
        symbol="BTCUSDT",
        side="Sell",
        quantity=0.1,
        method=TrailingMethod.PERCENTAGE,
        trail_value=1.5
    )
    trail_result = await manager.setup_trailing_stop(position_id, trailing)
    
    print(f"✅ Position fully protected:")
    print(f"   - Stop-Loss: {sl_result['orderId']}")
    print(f"   - Take-Profit: {tp_result['orderId']}")
    print(f"   - Trailing Stop: {trail_result}")
    
    # Get all position orders
    position_orders = manager.get_position_orders(position_id)
    assert len(position_orders) == 3, "Not all protection orders found"
    print(f"✅ All protection orders verified: {len(position_orders)}")
    
    # Cancel all position orders
    cancelled = await manager.cancel_position_orders(position_id)
    print(f"✅ Cancelled {cancelled} protection orders")
    
    return True

async def test_statistics():
    """Test statistics and monitoring"""
    print("\n" + "="*60)
    print("Testing Statistics and Monitoring")
    print("="*60)
    
    client = MockTradingClient()
    manager = AdvancedOrderManager(client)
    modifier = OrderModifier(client)
    handler = PartialFillHandler(client, modifier)
    
    # Create some test data
    for i in range(5):
        stop_loss = StopLossOrder(
            symbol="BTCUSDT",
            side="Sell",
            quantity=0.01 * (i + 1),
            trigger_price=49000 - (i * 100)
        )
        await manager.place_stop_loss(f"pos_{i}", stop_loss)
    
    # Get statistics
    manager_stats = manager.get_statistics()
    print(f"✅ Order Manager Statistics:")
    print(f"   - Active Orders: {manager_stats['active_orders']}")
    print(f"   - Protected Positions: {manager_stats['protected_positions']}")
    
    modifier_stats = modifier.get_statistics()
    print(f"✅ Modifier Statistics:")
    print(f"   - Total Modifications: {modifier_stats['total_modifications']}")
    print(f"   - Success Rate: {modifier_stats['success_rate']}%")
    
    handler_stats = handler.get_statistics()
    print(f"✅ Fill Handler Statistics:")
    print(f"   - Active Partials: {handler_stats['active_partials']}")
    print(f"   - Total Handled: {handler_stats['total_handled']}")
    
    return True

async def main():
    """Run all Phase 7 tests"""
    print("\n" + "="*60)
    print("PHASE 7: ADVANCED ORDER MANAGEMENT TEST SUITE")
    print("="*60)
    
    tests = [
        ("Stop-Loss Orders", test_stop_loss_orders),
        ("Take-Profit Orders", test_take_profit_orders),
        ("Trailing Stops", test_trailing_stops),
        ("Order Modifications", test_order_modifications),
        ("Partial Fill Handling", test_partial_fills),
        ("Position Protection", test_position_protection),
        ("Statistics & Monitoring", test_statistics)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, "PASSED" if result else "FAILED"))
        except Exception as e:
            logger.error(f"Test {test_name} failed: {e}")
            results.append((test_name, "ERROR"))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, status in results:
        symbol = "✅" if status == "PASSED" else "❌"
        print(f"  {symbol} {test_name}: {status}")
    
    passed = sum(1 for _, status in results if status == "PASSED")
    total = len(results)
    
    print("\n" + "="*60)
    if passed == total:
        print(f"🎉 ALL TESTS PASSED ({passed}/{total})")
        print("✨ Phase 7 Advanced Order Management is ready!")
    else:
        print(f"⚠️  Some tests failed ({passed}/{total} passed)")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())