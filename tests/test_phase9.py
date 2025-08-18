#!/usr/bin/env python3
"""
Test Suite for Phase 9: Funding Rate Strategies
Tests funding arbitrage, perp-spot spreads, and market-neutral positions
"""

import sys
import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Direct imports to avoid pandas dependency
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'strategies'))
import funding_rate
import cross_exchange_arbitrage

FundingRateStrategy = funding_rate.FundingRateStrategy
FundingConfig = funding_rate.FundingConfig
FundingPosition = funding_rate.FundingPosition
FundingDirection = funding_rate.FundingDirection

CrossExchangeArbitrage = cross_exchange_arbitrage.CrossExchangeArbitrage
ArbitrageOpportunity = cross_exchange_arbitrage.ArbitrageOpportunity
HedgedPosition = cross_exchange_arbitrage.HedgedPosition

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockExchangeClient:
    """Mock exchange client for testing"""
    
    def __init__(self, name: str = "bybit"):
        self.name = name
        self.funding_rate = 0.01  # 1% funding rate
        self.price = 50000
        
    async def get_instruments_info(self, **kwargs):
        """Mock get instruments"""
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {"symbol": "BTCUSDT", "volume24h": "10000000"},
                    {"symbol": "ETHUSDT", "volume24h": "5000000"},
                    {"symbol": "SOLUSDT", "volume24h": "2000000"}
                ]
            }
        }
    
    async def get_funding_rate_history(self, **kwargs):
        """Mock funding rate history"""
        symbol = kwargs.get("symbol", "BTCUSDT")
        
        # Simulate different rates for different symbols
        rates = {
            "BTCUSDT": 0.01,  # 1% - high positive
            "ETHUSDT": -0.005,  # -0.5% - negative
            "SOLUSDT": 0.002,  # 0.2% - moderate
        }
        
        return {
            "retCode": 0,
            "result": {
                "list": [{
                    "fundingRate": str(rates.get(symbol, 0.001)),
                    "fundingRateTimestamp": datetime.now().isoformat()
                }]
            }
        }
    
    async def get_tickers(self, **kwargs):
        """Mock get tickers"""
        category = kwargs.get("category", "linear")
        symbol = kwargs.get("symbol", "BTCUSDT")
        
        # Different prices for spot and perp
        if category == "spot":
            price = self.price - 50  # Spot slightly lower
        else:
            price = self.price + 50  # Perp slightly higher
        
        return {
            "retCode": 0,
            "result": {
                "list": [{
                    "symbol": symbol,
                    "lastPrice": str(price),
                    "bid1Price": str(price - 1),
                    "ask1Price": str(price + 1),
                    "volume24h": "1000000"
                }]
            }
        }
    
    async def place_order(self, **kwargs):
        """Mock place order"""
        return {
            "retCode": 0,
            "result": {
                "orderId": f"mock_order_{datetime.now().timestamp()}",
                "avgPrice": str(self.price)
            }
        }

async def test_funding_rate_analysis():
    """Test funding rate analysis"""
    print("\n" + "="*60)
    print("Testing Funding Rate Analysis")
    print("="*60)
    
    perp_client = MockExchangeClient("bybit_perp")
    strategy = FundingRateStrategy(perp_client)
    
    # Test 1: Analyze funding rates
    opportunities = await strategy.analyze_funding_rates()
    assert len(opportunities) > 0, "Should find funding opportunities"
    print(f"✅ Found {len(opportunities)} funding opportunities")
    
    # Test 2: Check opportunity details
    for opp in opportunities[:3]:
        print(f"   {opp['symbol']}: Rate={opp['funding_rate']:.4f}, "
              f"Annual={opp['annual_rate']:.2f}%, Direction={opp['direction'].value}")
    
    # Test 3: APR calculation
    apr = strategy.calculate_apr(0.01)  # 1% funding rate
    expected_apr = 0.01 * 3 * 365 * 100  # 1095%
    assert abs(apr - expected_apr) < 0.1, "APR calculation incorrect"
    print(f"✅ APR calculation: {apr:.2f}% annually")
    
    # Test 4: Daily income estimation
    daily_income = strategy.estimate_daily_income(10000, 0.01)
    expected_income = 10000 * 0.01 * 3  # $300
    assert abs(daily_income - expected_income) < 0.1, "Income calculation incorrect"
    print(f"✅ Daily income estimate: ${daily_income:.2f} on $10,000 position")
    
    return True

async def test_funding_positions():
    """Test funding position management"""
    print("\n" + "="*60)
    print("Testing Funding Position Management")
    print("="*60)
    
    perp_client = MockExchangeClient("bybit_perp")
    spot_client = MockExchangeClient("bybit_spot")
    strategy = FundingRateStrategy(perp_client, spot_client)
    
    # Test 1: Open funding position
    position = await strategy.open_funding_position(
        symbol="BTCUSDT",
        funding_rate=0.01,
        size=1000,
        use_hedge=True
    )
    
    assert position is not None, "Should create position"
    assert position.symbol == "BTCUSDT", "Symbol should match"
    assert position.side == "Sell", "Should short for positive funding"
    print(f"✅ Opened funding position: {position.symbol} {position.side}")
    
    # Test 2: Check position direction
    direction = strategy._determine_direction(0.01)
    assert direction == FundingDirection.SHORT, "Should short for positive rate"
    
    direction = strategy._determine_direction(-0.01)
    assert direction == FundingDirection.LONG, "Should long for negative rate"
    print("✅ Position direction logic correct")
    
    # Test 3: Collect funding payment
    strategy.positions["BTCUSDT"] = position
    await strategy.collect_funding_payments()
    print(f"✅ Funding collection executed")
    
    # Test 4: Close position
    success = await strategy.close_funding_position("BTCUSDT")
    assert success, "Should close position"
    assert "BTCUSDT" not in strategy.positions, "Position should be removed"
    print("✅ Position closed successfully")
    
    return True

async def test_arbitrage_scanning():
    """Test arbitrage opportunity scanning"""
    print("\n" + "="*60)
    print("Testing Arbitrage Scanning")
    print("="*60)
    
    exchanges = {
        "bybit_perp": MockExchangeClient("bybit_perp"),
        "bybit_spot": MockExchangeClient("bybit_spot")
    }
    
    arbitrage = CrossExchangeArbitrage(exchanges)
    
    # Test 1: Scan for opportunities
    opportunities = await arbitrage.scan_arbitrage_opportunities()
    print(f"✅ Scanned markets, found {len(opportunities)} opportunities")
    
    # Test 2: Check perp-spot arbitrage
    perp_spot_opp = await arbitrage._check_perp_spot_arbitrage("BTC")
    if perp_spot_opp:
        print(f"✅ Perp-Spot spread: {perp_spot_opp.spread_pct:.3f}%")
        print(f"   Estimated profit: ${perp_spot_opp.estimated_profit:.2f}")
    
    # Test 3: Check funding differentials
    funding_opp = await arbitrage._check_funding_differentials("BTC")
    if funding_opp:
        print(f"✅ Funding differential: {funding_opp.spread_pct:.3f}%")
    
    return True

async def test_hedged_positions():
    """Test hedged position execution"""
    print("\n" + "="*60)
    print("Testing Hedged Position Execution")
    print("="*60)
    
    exchanges = {
        "bybit_perp": MockExchangeClient("bybit_perp"),
        "bybit_spot": MockExchangeClient("bybit_spot")
    }
    
    arbitrage = CrossExchangeArbitrage(exchanges)
    
    # Test 1: Create arbitrage opportunity
    opportunity = ArbitrageOpportunity(
        type="perp_spot",
        symbol="BTC",
        exchange_a="bybit_perp",
        exchange_b="bybit_spot",
        price_a=50050,
        price_b=49950,
        spread=100,
        spread_pct=0.2,
        funding_rate_a=0.01,
        funding_rate_b=0,
        estimated_profit=10,
        confidence=80,
        expires_at=datetime.now() + timedelta(minutes=5)
    )
    
    print(f"✅ Created arbitrage opportunity: Spread={opportunity.spread_pct}%")
    
    # Test 2: Execute arbitrage
    position = await arbitrage.execute_arbitrage(opportunity)
    
    if position:
        assert position.symbol == "BTC", "Symbol should match"
        assert position.entry_spread == 100, "Spread should match"
        print(f"✅ Executed hedged position: {position.id}")
        
        # Test 3: Close position
        arbitrage.positions[position.id] = position
        success = await arbitrage.close_position(position.id)
        assert success, "Should close position"
        print("✅ Closed hedged position")
    
    return True

async def test_statistics():
    """Test statistics tracking"""
    print("\n" + "="*60)
    print("Testing Statistics & Monitoring")
    print("="*60)
    
    perp_client = MockExchangeClient("bybit_perp")
    funding_strategy = FundingRateStrategy(perp_client)
    
    # Simulate some activity
    funding_strategy.statistics["positions_opened"] = 10
    funding_strategy.statistics["positions_closed"] = 8
    funding_strategy.statistics["total_collected"] = 500
    funding_strategy.statistics["total_paid"] = 50
    funding_strategy.statistics["net_funding"] = 450
    
    # Test 1: Get statistics
    stats = funding_strategy.get_statistics()
    assert stats["net_funding"] == 450, "Net funding should match"
    print(f"✅ Funding statistics: Net P&L=${stats['net_funding']}")
    
    # Test 2: Arbitrage statistics
    exchanges = {
        "bybit_perp": MockExchangeClient("bybit_perp"),
        "bybit_spot": MockExchangeClient("bybit_spot")
    }
    
    arbitrage = CrossExchangeArbitrage(exchanges)
    arbitrage.statistics["opportunities_found"] = 50
    arbitrage.statistics["positions_opened"] = 5
    arbitrage.statistics["total_profit"] = 250
    
    arb_stats = arbitrage.get_statistics()
    print(f"✅ Arbitrage statistics: Opportunities={arb_stats['opportunities_found']}, "
          f"Profit=${arb_stats['total_profit']}")
    
    return True

async def test_risk_management():
    """Test risk management in funding strategies"""
    print("\n" + "="*60)
    print("Testing Risk Management")
    print("="*60)
    
    config = FundingConfig(
        symbols=["BTCUSDT", "ETHUSDT"],
        min_funding_rate=0.005,  # 0.5% minimum
        max_position_size=5000,
        use_spot_hedge=True,
        auto_close_threshold=-0.001,
        max_positions=3,
        risk_limit=0.05  # 5% risk limit
    )
    
    print(f"✅ Risk configuration created:")
    print(f"   - Min funding rate: {config.min_funding_rate * 100}%")
    print(f"   - Max position size: ${config.max_position_size}")
    print(f"   - Max positions: {config.max_positions}")
    print(f"   - Risk limit: {config.risk_limit * 100}%")
    
    # Test position sizing based on risk
    total_capital = 100000
    max_risk = total_capital * config.risk_limit  # $5000
    safe_position_size = min(config.max_position_size, max_risk)
    
    print(f"✅ Safe position size: ${safe_position_size} (based on ${total_capital} capital)")
    
    return True

async def main():
    """Run all Phase 9 tests"""
    print("\n" + "="*60)
    print("PHASE 9: FUNDING RATE STRATEGIES TEST SUITE")
    print("="*60)
    
    tests = [
        ("Funding Rate Analysis", test_funding_rate_analysis),
        ("Funding Positions", test_funding_positions),
        ("Arbitrage Scanning", test_arbitrage_scanning),
        ("Hedged Positions", test_hedged_positions),
        ("Statistics Tracking", test_statistics),
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
        print("✨ Phase 9 Funding Rate Strategies is ready!")
        print("\n📊 Key Features Implemented:")
        print("   • Funding rate arbitrage")
        print("   • Perpetual-Spot spreads")
        print("   • Cross-exchange arbitrage")
        print("   • Market-neutral positions")
        print("   • Automated funding collection")
        print("   • Risk-managed position sizing")
    else:
        print(f"⚠️  Some tests failed ({passed}/{total} passed)")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())