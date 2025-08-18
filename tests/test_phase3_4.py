#!/usr/bin/env python3
"""
Test script for Phase 3 (Risk Management) and Phase 4 (ML & Backtesting)
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

# Import modules to test
from risk_management.risk_manager import RiskManager
from risk_management.performance_analytics import PerformanceAnalytics
from risk_management.alert_system import AlertSystem, Alert, AlertPriority, AlertType
from ml_engine.price_predictor import PricePredictor
from backtesting.backtest_engine import BacktestEngine, BacktestResult

def print_section(title):
    """Print formatted section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_risk_manager():
    """Test Risk Management System"""
    print_section("TESTING RISK MANAGEMENT SYSTEM")
    
    # Initialize Risk Manager
    config = {
        'max_risk_per_trade': 0.02,
        'max_leverage': 10,
        'stop_loss_pct': 0.02
    }
    risk_manager = RiskManager(config)
    
    # Test 1: Position Size Calculation
    print("\n1. Testing Position Size Calculator:")
    balance = 10000
    entry_price = 50000
    stop_loss_price = 49000
    leverage = 5
    
    position_size, metrics = risk_manager.calculate_position_size(
        balance, entry_price, stop_loss_price, leverage
    )
    
    print(f"   Balance: ${balance}")
    print(f"   Entry Price: ${entry_price}")
    print(f"   Stop Loss: ${stop_loss_price}")
    print(f"   Leverage: {leverage}x")
    print(f"   → Position Size: {position_size:.4f} BTC")
    print(f"   → Risk Amount: ${metrics['risk_amount']:.2f}")
    print(f"   → Risk Percentage: {metrics['risk_percentage']:.2f}%")
    
    # Test 2: Trade Validation
    print("\n2. Testing Trade Validation:")
    current_positions = []
    proposed_trade = {
        'size': position_size,
        'price': entry_price,
        'stop_loss': stop_loss_price,
        'take_profit': 52000
    }
    
    is_valid, reason = risk_manager.validate_trade(balance, current_positions, proposed_trade)
    print(f"   Trade Valid: {is_valid}")
    print(f"   Reason: {reason}")
    
    # Test 3: Risk Score
    print("\n3. Testing Risk Score Calculation:")
    positions = [
        {'symbol': 'BTCUSDT', 'size': 0.01, 'markPrice': 50000, 'unrealizedPnl': 50},
        {'symbol': 'ETHUSDT', 'size': 0.1, 'markPrice': 3000, 'unrealizedPnl': -20}
    ]
    
    risk_score = risk_manager.get_risk_score(balance, positions)
    print(f"   Risk Score: {risk_score['risk_score']}/100")
    print(f"   Risk Level: {risk_score['risk_level']}")
    print(f"   Exposure: {risk_score['exposure_percent']:.2f}%")
    print(f"   Can Trade: {risk_score['can_trade']}")
    
    return "✅ Risk Management tests passed"

def test_performance_analytics():
    """Test Performance Analytics"""
    print_section("TESTING PERFORMANCE ANALYTICS")
    
    analytics = PerformanceAnalytics()
    
    # Add sample trades
    print("\n1. Adding Sample Trades:")
    trades = [
        {'symbol': 'BTCUSDT', 'pnl': 100, 'volume': 1000, 'fees': 2, 'timestamp': datetime.now() - timedelta(days=5)},
        {'symbol': 'BTCUSDT', 'pnl': -50, 'volume': 800, 'fees': 1.5, 'timestamp': datetime.now() - timedelta(days=4)},
        {'symbol': 'ETHUSDT', 'pnl': 75, 'volume': 1200, 'fees': 2.5, 'timestamp': datetime.now() - timedelta(days=3)},
        {'symbol': 'BTCUSDT', 'pnl': -30, 'volume': 600, 'fees': 1, 'timestamp': datetime.now() - timedelta(days=2)},
        {'symbol': 'ETHUSDT', 'pnl': 120, 'volume': 1500, 'fees': 3, 'timestamp': datetime.now() - timedelta(days=1)},
    ]
    
    for trade in trades:
        analytics.add_trade(trade)
    print(f"   Added {len(trades)} trades")
    
    # Calculate metrics
    print("\n2. Performance Metrics:")
    metrics = analytics.calculate_metrics(period_days=30)
    
    print(f"   Total Trades: {metrics['total_trades']}")
    print(f"   Win Rate: {metrics['win_rate']:.1f}%")
    print(f"   Total P&L: ${metrics['total_pnl']:.2f}")
    print(f"   Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"   Max Drawdown: ${metrics['max_drawdown']:.2f}")
    print(f"   Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"   Expectancy: ${metrics['expectancy']:.2f}")
    
    # Get daily breakdown
    print("\n3. Daily Breakdown:")
    daily = analytics.get_daily_breakdown(days=7)
    for day in daily[-3:]:  # Last 3 days
        print(f"   {day['date']}: {day['trades']} trades, P&L: ${day['pnl']:.2f}")
    
    return "✅ Performance Analytics tests passed"

def test_alert_system():
    """Test Alert System"""
    print_section("TESTING ALERT SYSTEM")
    
    alert_system = AlertSystem()
    
    # Test 1: Create alerts
    print("\n1. Creating Alerts:")
    
    # High risk alert
    alert1 = Alert(
        AlertType.RISK,
        AlertPriority.HIGH,
        "High Risk Level",
        "Risk score exceeded 75",
        {'risk_score': 78}
    )
    alert_system.add_alert(alert1)
    print("   Added HIGH risk alert")
    
    # Price alert
    alert2 = Alert(
        AlertType.PRICE,
        AlertPriority.MEDIUM,
        "BTC Price Alert",
        "BTC reached $51,000",
        {'symbol': 'BTCUSDT', 'price': 51000}
    )
    alert_system.add_alert(alert2)
    print("   Added MEDIUM price alert")
    
    # Position alert
    alert3 = Alert(
        AlertType.POSITION,
        AlertPriority.LOW,
        "Position Update",
        "ETH position opened",
        {'symbol': 'ETHUSDT', 'size': 0.1}
    )
    alert_system.add_alert(alert3)
    print("   Added LOW position alert")
    
    # Test 2: Get alerts
    print("\n2. Alert Summary:")
    summary = alert_system.get_alert_summary()
    print(f"   Total Alerts: {summary['total_alerts']}")
    print(f"   Unread: {summary['unread_alerts']}")
    print(f"   By Priority: {summary['by_priority']}")
    
    # Test 3: Check risk alerts
    print("\n3. Testing Risk Alert Triggers:")
    risk_metrics = {
        'risk_score': 82,
        'risk_level': 'CRITICAL',
        'consecutive_losses': 4,
        'daily_pnl_percent': -4.5
    }
    alert_system.check_risk_alerts(risk_metrics)
    
    new_summary = alert_system.get_alert_summary()
    print(f"   New alerts added: {new_summary['total_alerts'] - summary['total_alerts']}")
    
    return "✅ Alert System tests passed"

def test_ml_predictor():
    """Test ML Price Predictor"""
    print_section("TESTING ML PRICE PREDICTOR")
    
    predictor = PricePredictor()
    
    # Generate sample data
    print("\n1. Generating Sample Data:")
    dates = pd.date_range(end=datetime.now(), periods=500, freq='1H')
    
    # Create realistic OHLCV data
    np.random.seed(42)
    base_price = 50000
    prices = []
    
    for i in range(len(dates)):
        change = np.random.randn() * 0.002  # 0.2% volatility
        base_price *= (1 + change)
        prices.append(base_price)
    
    df = pd.DataFrame({
        'open': prices,
        'high': [p * 1.001 for p in prices],
        'low': [p * 0.999 for p in prices],
        'close': [p * (1 + np.random.randn() * 0.0005) for p in prices],
        'volume': np.random.uniform(1000, 5000, len(dates))
    }, index=dates)
    
    print(f"   Generated {len(df)} hourly candles")
    print(f"   Date range: {df.index[0]} to {df.index[-1]}")
    
    # Test 2: Feature extraction
    print("\n2. Extracting Features:")
    features = predictor.extract_features(df)
    print(f"   Extracted {len(features.columns)} features")
    print(f"   Sample features: {list(features.columns[:5])}")
    
    # Test 3: Train model
    print("\n3. Training ML Models:")
    predictor.train(df, model_type='ensemble')
    
    # Test 4: Make prediction
    print("\n4. Making Predictions:")
    prediction = predictor.predict(df, confidence_threshold=0.5)
    
    print(f"   Predicted Change: {prediction['predicted_change']*100:.3f}%")
    print(f"   Confidence: {prediction['confidence']*100:.1f}%")
    print(f"   Signal: {prediction['signal']}")
    print(f"   Current Price: ${prediction['current_price']:.2f}")
    print(f"   Predicted Price: ${prediction['predicted_price']:.2f}")
    
    # Test 5: Evaluate predictions
    print("\n5. Model Evaluation:")
    evaluation = predictor.evaluate_predictions(lookback_hours=24)
    print(f"   Direction Accuracy: {evaluation['direction_accuracy']*100:.1f}%")
    print(f"   MAE: {evaluation['mae']:.4f}")
    print(f"   R² Score: {evaluation['r2_score']:.3f}")
    
    return "✅ ML Predictor tests passed"

def test_backtesting():
    """Test Backtesting Engine"""
    print_section("TESTING BACKTESTING ENGINE")
    
    # Initialize backtesting engine
    config = {
        'initial_capital': 10000,
        'commission': 0.0006,
        'slippage': 0.0001,
        'position_size': 0.1,
        'use_stop_loss': True,
        'stop_loss_pct': 0.02,
        'use_take_profit': True,
        'take_profit_pct': 0.04
    }
    engine = BacktestEngine(config)
    
    # Generate sample data
    print("\n1. Preparing Test Data:")
    dates = pd.date_range(end=datetime.now(), periods=1000, freq='1H')
    base_price = 50000
    prices = []
    
    for i in range(len(dates)):
        trend = np.sin(i/100) * 0.001  # Add trend
        noise = np.random.randn() * 0.002
        base_price *= (1 + trend + noise)
        prices.append(base_price)
    
    df = pd.DataFrame({
        'open': prices,
        'high': [p * 1.002 for p in prices],
        'low': [p * 0.998 for p in prices],
        'close': [p * (1 + np.random.randn() * 0.0001) for p in prices],
        'volume': np.random.uniform(1000, 5000, len(dates))
    }, index=dates)
    
    print(f"   Test period: {df.index[0]} to {df.index[-1]}")
    print(f"   Total bars: {len(df)}")
    
    # Create simple strategy for testing
    class SimpleStrategy:
        def generate_signals(self, data):
            """Generate buy/sell signals based on simple MA crossover"""
            signals = pd.Series(0, index=data.index)
            
            # Simple moving averages
            sma_fast = data['close'].rolling(10).mean()
            sma_slow = data['close'].rolling(30).mean()
            
            # Generate signals
            signals[sma_fast > sma_slow] = 1   # Buy signal
            signals[sma_fast < sma_slow] = -1  # Sell signal
            
            # Only trade every N bars to limit trades
            signals = signals[::20]  # Trade every 20 bars
            
            return signals.reindex(data.index, fill_value=0)
    
    # Test 2: Run backtest
    print("\n2. Running Backtest:")
    strategy = SimpleStrategy()
    result = engine.run(df, strategy)
    
    # Test 3: Display results
    print("\n3. Backtest Results:")
    print(f"   Total Return: {result.total_return*100:.2f}%")
    print(f"   Total P&L: ${result.total_pnl:.2f}")
    print(f"   Total Trades: {result.total_trades}")
    print(f"   Win Rate: {result.win_rate*100:.1f}%")
    print(f"   Profit Factor: {result.profit_factor:.2f}")
    print(f"   Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"   Max Drawdown: {result.max_drawdown*100:.1f}%")
    print(f"   Average Win: ${result.avg_win:.2f}")
    print(f"   Average Loss: ${result.avg_loss:.2f}")
    print(f"   Expectancy: ${result.expectancy:.2f}")
    
    # Test 4: Generate report
    print("\n4. Performance Report:")
    report = engine.generate_report(result)
    print(report.split('\n')[0:5])  # Print first few lines
    
    return "✅ Backtesting Engine tests passed"

def main():
    """Run all tests"""
    print("\n" + "🚀"*30)
    print("  PHASE 3 & 4 TESTING SUITE")
    print("🚀"*30)
    
    results = []
    
    # Test Risk Management
    try:
        result = test_risk_manager()
        results.append(result)
    except Exception as e:
        results.append(f"❌ Risk Manager failed: {e}")
    
    # Test Performance Analytics
    try:
        result = test_performance_analytics()
        results.append(result)
    except Exception as e:
        results.append(f"❌ Performance Analytics failed: {e}")
    
    # Test Alert System
    try:
        result = test_alert_system()
        results.append(result)
    except Exception as e:
        results.append(f"❌ Alert System failed: {e}")
    
    # Test ML Predictor
    try:
        result = test_ml_predictor()
        results.append(result)
    except Exception as e:
        results.append(f"❌ ML Predictor failed: {e}")
    
    # Test Backtesting
    try:
        result = test_backtesting()
        results.append(result)
    except Exception as e:
        results.append(f"❌ Backtesting failed: {e}")
    
    # Summary
    print_section("TEST SUMMARY")
    print()
    for result in results:
        print(f"  {result}")
    
    # Overall result
    passed = sum(1 for r in results if "✅" in r)
    total = len(results)
    
    print()
    print("="*60)
    if passed == total:
        print(f"  🎉 ALL TESTS PASSED ({passed}/{total})")
    else:
        print(f"  ⚠️ SOME TESTS FAILED ({passed}/{total})")
    print("="*60)

if __name__ == "__main__":
    main()