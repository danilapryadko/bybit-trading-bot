#!/usr/bin/env python3
"""
Test Suite for Phase 8: Grid Trading Strategy
Tests grid trading, optimization, and auto-compounding
"""

import sys
import os
import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.grid_trading import (
    GridTradingStrategy,
    GridConfig,
    GridType,
    GridDirection,
    GridLevel
)
from strategies.grid_optimizer import (
    GridOptimizer,
    OptimizationResult
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
        self.order_counter = 2000
        self.current_price = 50000
        
    async def place_order(self, **kwargs):
        """Mock place order"""
        order_id = f"grid_{self.order_counter}"
        self.order_counter += 1
        
        self.orders[order_id] = {
            "orderId": order_id,
            "symbol": kwargs.get("symbol"),
            "side": kwargs.get("side"),
            "orderType": kwargs.get("orderType"),
            "qty": kwargs.get("qty"),
            "price": kwargs.get("price"),
            "status": "New"
        }
        
        return {
            "retCode": 0,
            "result": {"orderId": order_id}
        }
    
    async def cancel_order(self, **kwargs):
        """Mock cancel order"""
        order_id = kwargs.get("orderId")
        if order_id in self.orders:
            self.orders[order_id]["status"] = "Cancelled"
            return {"retCode": 0}
        return {"retCode": 1}
    
    async def get_open_orders(self, **kwargs):
        """Mock get open orders"""
        open_orders = [
            order for order in self.orders.values()
            if order["status"] == "New"
        ]
        
        return {
            "retCode": 0,
            "result": {"list": open_orders}
        }
    
    async def get_tickers(self, **kwargs):
        """Mock get tickers"""
        # Simulate price movement
        self.current_price += np.random.randint(-100, 100)
        
        return {
            "retCode": 0,
            "result": {
                "list": [{
                    "symbol": kwargs.get("symbol", "BTCUSDT"),
                    "lastPrice": str(self.current_price)
                }]
            }
        }
    
    def simulate_fill(self, order_id: str):
        """Simulate order fill for testing"""
        if order_id in self.orders:
            self.orders[order_id]["status"] = "Filled"

class MockDataProvider:
    """Mock market data provider"""
    
    async def get_historical_data(self, symbol: str, timeframe: str, days: int) -> pd.DataFrame:
        """Generate mock historical data"""
        periods = days * 24 if timeframe == "1h" else days
        
        # Generate synthetic price data
        dates = pd.date_range(end=datetime.now(), periods=periods, freq=timeframe)
        prices = 50000 + np.cumsum(np.random.randn(periods) * 100)
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.randn(periods) * 50,
            'high': prices + abs(np.random.randn(periods) * 100),
            'low': prices - abs(np.random.randn(periods) * 100),
            'close': prices,
            'volume': np.random.randint(100, 1000, periods)
        })
        
        return data

async def test_grid_types():
    """Test different grid types"""
    print("\n" + "="*60)
    print("Testing Grid Types")
    print("="*60)
    
    client = MockTradingClient()
    
    # Test 1: Fixed grid
    config_fixed = GridConfig(
        symbol="BTCUSDT",
        grid_type=GridType.FIXED,
        direction=GridDirection.NEUTRAL,
        upper_price=52000,
        lower_price=48000,
        grid_levels=10,
        total_investment=1000
    )
    
    strategy_fixed = GridTradingStrategy(client, config_fixed)
    levels_fixed = strategy_fixed.calculate_grid_levels()
    
    assert len(levels_fixed) == 10, "Fixed grid should have 10 levels"
    print(f"✅ Fixed grid created with {len(levels_fixed)} levels")
    
    # Test 2: Dynamic grid
    config_dynamic = GridConfig(
        symbol="BTCUSDT",
        grid_type=GridType.DYNAMIC,
        direction=GridDirection.NEUTRAL,
        upper_price=52000,
        lower_price=48000,
        grid_levels=8,
        total_investment=1000
    )
    
    strategy_dynamic = GridTradingStrategy(client, config_dynamic)
    levels_dynamic = strategy_dynamic.calculate_grid_levels()
    
    assert len(levels_dynamic) == 8, "Dynamic grid should have 8 levels"
    print(f"✅ Dynamic grid created with {len(levels_dynamic)} levels")
    
    # Test 3: Geometric grid
    config_geometric = GridConfig(
        symbol="BTCUSDT",
        grid_type=GridType.GEOMETRIC,
        direction=GridDirection.LONG,
        upper_price=55000,
        lower_price=45000,
        grid_levels=12,
        total_investment=2000
    )
    
    strategy_geometric = GridTradingStrategy(client, config_geometric)
    levels_geometric = strategy_geometric.calculate_grid_levels()
    
    assert len(levels_geometric) == 12, "Geometric grid should have 12 levels"
    assert all(level.side == "Buy" for level in levels_geometric if level.price < 50000), "Long grid should have buy orders"
    print(f"✅ Geometric grid created with {len(levels_geometric)} levels")
    
    # Test 4: Fibonacci grid
    config_fib = GridConfig(
        symbol="BTCUSDT",
        grid_type=GridType.FIBONACCI,
        direction=GridDirection.SHORT,
        upper_price=51000,
        lower_price=49000,
        grid_levels=7,
        total_investment=1500
    )
    
    strategy_fib = GridTradingStrategy(client, config_fib)
    levels_fib = strategy_fib.calculate_grid_levels()
    
    assert len(levels_fib) == 7, "Fibonacci grid should have 7 levels"
    print(f"✅ Fibonacci grid created with {len(levels_fib)} levels")
    
    return True

async def test_grid_trading():
    """Test grid trading operations"""
    print("\n" + "="*60)
    print("Testing Grid Trading Operations")
    print("="*60)
    
    client = MockTradingClient()
    
    config = GridConfig(
        symbol="BTCUSDT",
        grid_type=GridType.FIXED,
        direction=GridDirection.NEUTRAL,
        upper_price=51000,
        lower_price=49000,
        grid_levels=5,
        total_investment=1000,
        max_open_orders=10
    )
    
    strategy = GridTradingStrategy(client, config)
    
    # Test 1: Start grid
    await strategy.start_grid()
    assert strategy.grid_active, "Grid should be active"
    print("✅ Grid trading started")
    
    # Test 2: Check orders placed
    await asyncio.sleep(0.1)  # Give time for orders to be placed
    assert len(strategy.active_orders) > 0, "Should have active orders"
    print(f"✅ Placed {len(strategy.active_orders)} grid orders")
    
    # Test 3: Simulate order fill
    if strategy.active_orders:
        first_order_id = list(strategy.active_orders.keys())[0]
        client.simulate_fill(first_order_id)
        
        # Process filled order
        await strategy._check_filled_orders()
        assert first_order_id not in strategy.active_orders, "Filled order should be removed"
        print("✅ Order fill handled correctly")
    
    # Test 4: Get grid status
    status = strategy.get_grid_status()
    assert status["active"], "Grid should be active"
    assert status["symbol"] == "BTCUSDT", "Symbol should match"
    print(f"✅ Grid status: {status['levels']} levels, {status['active_orders']} active")
    
    # Test 5: Stop grid
    await strategy.stop_grid()
    assert not strategy.grid_active, "Grid should be stopped"
    print("✅ Grid trading stopped")
    
    return True

async def test_grid_adjustments():
    """Test dynamic grid adjustments"""
    print("\n" + "="*60)
    print("Testing Grid Adjustments")
    print("="*60)
    
    client = MockTradingClient()
    
    config = GridConfig(
        symbol="BTCUSDT",
        grid_type=GridType.DYNAMIC,
        direction=GridDirection.NEUTRAL,
        upper_price=52000,
        lower_price=48000,
        grid_levels=6,
        total_investment=2000,
        volatility_adjustment=True,
        rebalance_interval=timedelta(seconds=1)  # Fast rebalance for testing
    )
    
    strategy = GridTradingStrategy(client, config)
    await strategy.start_grid()
    
    # Test 1: Grid shift up
    original_upper = config.upper_price
    await strategy._shift_grid(500)  # Shift up by $500
    assert config.upper_price > original_upper, "Upper price should increase"
    print(f"✅ Grid shifted up: {original_upper} -> {config.upper_price}")
    
    # Test 2: Grid shift down
    original_lower = config.lower_price
    await strategy._shift_grid(-500)  # Shift down by $500
    assert config.lower_price < original_lower, "Lower price should decrease"
    print(f"✅ Grid shifted down: {original_lower} -> {config.lower_price}")
    
    # Test 3: Spacing adjustment
    original_range = config.upper_price - config.lower_price
    await strategy._adjust_grid_spacing(1.5)  # Widen by 50%
    new_range = config.upper_price - config.lower_price
    assert new_range > original_range, "Range should widen"
    print(f"✅ Grid spacing adjusted: range {original_range:.0f} -> {new_range:.0f}")
    
    # Test 4: Rebalance trigger
    strategy.last_rebalance = datetime.now() - timedelta(hours=5)
    await strategy._rebalance_grid()
    assert strategy.last_rebalance > datetime.now() - timedelta(minutes=1), "Should have rebalanced"
    print("✅ Grid rebalanced based on market conditions")
    
    await strategy.stop_grid()
    
    return True

async def test_auto_compounding():
    """Test auto-compounding functionality"""
    print("\n" + "="*60)
    print("Testing Auto-Compounding")
    print("="*60)
    
    client = MockTradingClient()
    
    config = GridConfig(
        symbol="BTCUSDT",
        grid_type=GridType.FIXED,
        direction=GridDirection.NEUTRAL,
        upper_price=51000,
        lower_price=49000,
        grid_levels=5,
        total_investment=1000,
        auto_compound=True,
        compound_threshold=50  # Low threshold for testing
    )
    
    strategy = GridTradingStrategy(client, config)
    await strategy.start_grid()
    
    # Test 1: Simulate profits
    original_investment = config.total_investment
    strategy.total_profit = 100  # Simulate $100 profit
    
    # Test 2: Trigger compound check
    await strategy._check_compound()
    
    assert config.total_investment > original_investment, "Investment should increase after compounding"
    assert strategy.statistics["compounds_executed"] > 0, "Should have executed compound"
    print(f"✅ Compounded profits: ${original_investment} -> ${config.total_investment}")
    
    # Test 3: Check grid level adjustments
    for level in strategy.grid_levels:
        assert level.quantity > 0, "Grid quantities should be positive"
    print("✅ Grid quantities adjusted after compounding")
    
    await strategy.stop_grid()
    
    return True

async def test_grid_optimizer():
    """Test grid optimization"""
    print("\n" + "="*60)
    print("Testing Grid Optimizer")
    print("="*60)
    
    data_provider = MockDataProvider()
    optimizer = GridOptimizer(data_provider)
    
    # Test 1: Generate test data
    test_data = await data_provider.get_historical_data("BTCUSDT", "1h", 30)
    assert not test_data.empty, "Should have historical data"
    print(f"✅ Generated {len(test_data)} periods of test data")
    
    # Test 2: Analyze market structure
    analysis = optimizer._analyze_market_structure(test_data)
    assert "trend" in analysis, "Should have trend analysis"
    assert "volatility" in analysis, "Should have volatility analysis"
    assert "regime" in analysis, "Should have regime detection"
    print(f"✅ Market analysis: {analysis['regime']} regime, {analysis['trend']} trend")
    
    # Test 3: Find optimal range
    upper, lower = optimizer._find_optimal_range(test_data, analysis)
    assert upper > lower, "Upper should be greater than lower"
    print(f"✅ Optimal range: ${lower:.0f} - ${upper:.0f}")
    
    # Test 4: Calculate optimal levels
    levels = optimizer._calculate_optimal_levels(upper, lower, 10000, test_data)
    assert 5 <= levels <= 50, "Levels should be in reasonable range"
    print(f"✅ Optimal grid levels: {levels}")
    
    # Test 5: Determine spacing type
    spacing = optimizer._determine_spacing_type(analysis)
    assert spacing in ["fixed", "dynamic", "geometric", "fibonacci"], "Should return valid spacing type"
    print(f"✅ Recommended spacing: {spacing}")
    
    # Test 6: Backtest strategy
    backtest_results = optimizer.backtest_grid_strategy(
        test_data, upper, lower, levels, 10000
    )
    print(f"✅ Backtest results: {backtest_results['total_trades']} trades, "
          f"{backtest_results['win_rate']:.1f}% win rate")
    
    return True

async def test_grid_statistics():
    """Test grid statistics and monitoring"""
    print("\n" + "="*60)
    print("Testing Grid Statistics")
    print("="*60)
    
    client = MockTradingClient()
    
    config = GridConfig(
        symbol="BTCUSDT",
        grid_type=GridType.FIXED,
        direction=GridDirection.NEUTRAL,
        upper_price=51000,
        lower_price=49000,
        grid_levels=8,
        total_investment=5000
    )
    
    strategy = GridTradingStrategy(client, config)
    await strategy.start_grid()
    
    # Simulate some trading activity
    strategy.statistics["grids_filled"] = 10
    strategy.statistics["total_volume"] = 50000
    strategy.total_profit = 250
    
    # Test 1: Update statistics
    strategy._update_statistics()
    assert strategy.statistics["avg_profit_per_grid"] > 0, "Should calculate average profit"
    print(f"✅ Average profit per grid: ${strategy.statistics['avg_profit_per_grid']:.2f}")
    
    # Test 2: Get grid status
    status = strategy.get_grid_status()
    assert "roi" in status, "Should calculate ROI"
    print(f"✅ Grid ROI: {status['roi']:.2f}%")
    
    # Test 3: Get grid levels display
    levels_display = strategy.get_grid_levels_display()
    assert len(levels_display) == 8, "Should have all levels for display"
    print(f"✅ Grid levels formatted for display: {len(levels_display)} levels")
    
    # Test 4: Performance metrics
    metrics = {
        "total_profit": strategy.total_profit,
        "grids_filled": strategy.statistics["grids_filled"],
        "win_rate": strategy.statistics.get("win_rate", 0),
        "compounds": strategy.statistics["compounds_executed"]
    }
    print(f"✅ Performance metrics: {metrics}")
    
    await strategy.stop_grid()
    
    return True

async def test_risk_management():
    """Test grid risk management"""
    print("\n" + "="*60)
    print("Testing Grid Risk Management")
    print("="*60)
    
    data_provider = MockDataProvider()
    optimizer = GridOptimizer(data_provider)
    
    # Generate volatile data
    test_data = await data_provider.get_historical_data("BTCUSDT", "1h", 30)
    
    # Add volatility
    test_data['close'] = test_data['close'] * (1 + np.random.randn(len(test_data)) * 0.05)
    
    analysis = optimizer._analyze_market_structure(test_data)
    
    # Test 1: Risk score calculation
    risk_score = optimizer._calculate_risk_score(test_data, analysis)
    assert 0 <= risk_score <= 100, "Risk score should be 0-100"
    print(f"✅ Risk score calculated: {risk_score}/100")
    
    # Test 2: Max drawdown calculation
    max_dd = optimizer._calculate_max_drawdown(test_data)
    assert 0 <= max_dd <= 1, "Drawdown should be 0-1"
    print(f"✅ Maximum drawdown: {max_dd*100:.2f}%")
    
    # Test 3: Generate recommendations
    recommendations = optimizer._generate_recommendations(analysis, risk_score)
    assert len(recommendations) > 0, "Should generate recommendations"
    print(f"✅ Generated {len(recommendations)} recommendations:")
    for rec in recommendations[:3]:
        print(f"   - {rec}")
    
    # Test 4: Confidence calculation
    confidence = optimizer._calculate_confidence(analysis)
    assert 0 <= confidence <= 100, "Confidence should be 0-100"
    print(f"✅ Strategy confidence: {confidence}%")
    
    return True

async def main():
    """Run all Phase 8 tests"""
    print("\n" + "="*60)
    print("PHASE 8: GRID TRADING STRATEGY TEST SUITE")
    print("="*60)
    
    tests = [
        ("Grid Types", test_grid_types),
        ("Grid Trading Operations", test_grid_trading),
        ("Grid Adjustments", test_grid_adjustments),
        ("Auto-Compounding", test_auto_compounding),
        ("Grid Optimizer", test_grid_optimizer),
        ("Grid Statistics", test_grid_statistics),
        ("Risk Management", test_risk_management)
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
        print("✨ Phase 8 Grid Trading Strategy is ready!")
    else:
        print(f"⚠️  Some tests failed ({passed}/{total} passed)")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())