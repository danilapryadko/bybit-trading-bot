#!/usr/bin/env python3
"""
Integration test for the complete trading system
Tests the interaction between all Phase 3 & 4 components
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
import json

# Import all components
from risk_management.risk_manager import RiskManager
from risk_management.performance_analytics import PerformanceAnalytics
from risk_management.alert_system import AlertSystem, Alert, AlertPriority, AlertType
from ml_engine.price_predictor import PricePredictor
from backtesting.backtest_engine import BacktestEngine
from strategies.rsi_strategy import RSIStrategy
from strategies.ma_strategy import MovingAverageStrategy
from strategies.manager import StrategyManager

def print_header(title):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

class IntegrationTest:
    """Complete system integration test"""
    
    def __init__(self):
        # Initialize all components
        self.risk_manager = RiskManager()
        self.performance = PerformanceAnalytics()
        self.alert_system = AlertSystem()
        self.ml_predictor = PricePredictor()
        self.backtest_engine = BacktestEngine()
        self.strategy_manager = StrategyManager()
        
        # Test data
        self.market_data = None
        self.balance = 10000
        
    def generate_market_data(self):
        """Generate realistic market data for testing"""
        print("\n📊 Generating Market Data...")
        
        # Generate 30 days of hourly data
        periods = 24 * 30  # 30 days
        dates = pd.date_range(end=datetime.now(), periods=periods, freq='1H')
        
        # Generate realistic price movement
        np.random.seed(42)
        base_price = 50000
        prices = []
        volumes = []
        
        for i in range(periods):
            # Add trend component
            trend = np.sin(i / 100) * 0.002
            
            # Add volatility
            volatility = np.random.randn() * 0.005
            
            # Update price
            base_price *= (1 + trend + volatility)
            prices.append(base_price)
            
            # Generate volume
            base_volume = 1000000
            volume_variation = np.random.uniform(0.5, 1.5)
            volumes.append(base_volume * volume_variation)
        
        # Create OHLCV dataframe
        self.market_data = pd.DataFrame({
            'open': prices,
            'high': [p * np.random.uniform(1.001, 1.005) for p in prices],
            'low': [p * np.random.uniform(0.995, 0.999) for p in prices],
            'close': [p * np.random.uniform(0.998, 1.002) for p in prices],
            'volume': volumes
        }, index=dates)
        
        print(f"   ✅ Generated {len(self.market_data)} candles")
        print(f"   📅 Period: {dates[0]} to {dates[-1]}")
        print(f"   💰 Price range: ${self.market_data['close'].min():.2f} - ${self.market_data['close'].max():.2f}")
        
    def test_ml_prediction_pipeline(self):
        """Test ML prediction with risk validation"""
        print_header("ML PREDICTION + RISK VALIDATION")
        
        # Train ML model
        print("\n1️⃣ Training ML Model...")
        self.ml_predictor.train(self.market_data, model_type='ensemble')
        
        # Make prediction
        print("\n2️⃣ Making Price Prediction...")
        prediction = self.ml_predictor.predict(self.market_data)
        
        print(f"   📈 Prediction: {prediction['signal']}")
        print(f"   🎯 Confidence: {prediction['confidence']*100:.1f}%")
        print(f"   💵 Current Price: ${prediction['current_price']:.2f}")
        print(f"   🔮 Predicted Change: {prediction['predicted_change']*100:.2f}%")
        
        # Validate with risk manager
        print("\n3️⃣ Risk Validation...")
        
        if prediction['signal'] != 'HOLD':
            # Calculate position size
            entry_price = prediction['current_price']
            stop_loss = entry_price * 0.98 if prediction['signal'] == 'BUY' else entry_price * 1.02
            
            position_size, risk_metrics = self.risk_manager.calculate_position_size(
                self.balance, entry_price, stop_loss, leverage=3
            )
            
            print(f"   📏 Position Size: {position_size:.4f} BTC")
            print(f"   ⚠️ Risk Amount: ${risk_metrics['risk_amount']:.2f}")
            print(f"   📊 Risk Percentage: {risk_metrics['risk_percentage']:.1f}%")
            
            # Check if trade is allowed
            is_valid, reason = self.risk_manager.validate_trade(
                self.balance, [], 
                {'size': position_size, 'price': entry_price}
            )
            
            print(f"   ✅ Trade Allowed: {is_valid}")
            if not is_valid:
                print(f"   ❌ Reason: {reason}")
        
        return prediction
    
    def test_strategy_backtest(self):
        """Test strategy with backtesting"""
        print_header("STRATEGY BACKTESTING")
        
        # Create and configure strategies
        print("\n1️⃣ Setting Up Strategies...")
        
        # RSI Strategy
        rsi_strategy = RSIStrategy('BTCUSDT', {
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70
        })
        
        # MA Strategy
        ma_strategy = MovingAverageStrategy('BTCUSDT', {
            'fast_period': 10,
            'slow_period': 30
        })
        
        print("   ✅ RSI Strategy configured")
        print("   ✅ MA Strategy configured")
        
        # Backtest RSI Strategy
        print("\n2️⃣ Backtesting RSI Strategy...")
        rsi_result = self.backtest_engine.run(
            self.market_data,
            rsi_strategy,
            start_date=self.market_data.index[0],
            end_date=self.market_data.index[-1]
        )
        
        print(f"   📈 Total Return: {rsi_result.total_return*100:.2f}%")
        print(f"   🎯 Win Rate: {rsi_result.win_rate*100:.1f}%")
        print(f"   📊 Sharpe Ratio: {rsi_result.sharpe_ratio:.2f}")
        print(f"   📉 Max Drawdown: {rsi_result.max_drawdown*100:.1f}%")
        
        # Backtest MA Strategy
        print("\n3️⃣ Backtesting MA Strategy...")
        self.backtest_engine.reset()
        ma_result = self.backtest_engine.run(
            self.market_data,
            ma_strategy,
            start_date=self.market_data.index[0],
            end_date=self.market_data.index[-1]
        )
        
        print(f"   📈 Total Return: {ma_result.total_return*100:.2f}%")
        print(f"   🎯 Win Rate: {ma_result.win_rate*100:.1f}%")
        print(f"   📊 Sharpe Ratio: {ma_result.sharpe_ratio:.2f}")
        print(f"   📉 Max Drawdown: {ma_result.max_drawdown*100:.1f}%")
        
        # Compare strategies
        print("\n4️⃣ Strategy Comparison:")
        if rsi_result.sharpe_ratio > ma_result.sharpe_ratio:
            print("   🏆 RSI Strategy performs better")
        else:
            print("   🏆 MA Strategy performs better")
        
        return rsi_result, ma_result
    
    def test_risk_monitoring(self):
        """Test risk monitoring and alerts"""
        print_header("RISK MONITORING & ALERTS")
        
        # Simulate trading session
        print("\n1️⃣ Simulating Trading Session...")
        
        # Add some trades to performance tracker
        trades = [
            {'symbol': 'BTCUSDT', 'pnl': 150, 'volume': 5000, 'fees': 3, 'timestamp': datetime.now() - timedelta(hours=5)},
            {'symbol': 'BTCUSDT', 'pnl': -80, 'volume': 4000, 'fees': 2.5, 'timestamp': datetime.now() - timedelta(hours=4)},
            {'symbol': 'ETHUSDT', 'pnl': 200, 'volume': 6000, 'fees': 3.5, 'timestamp': datetime.now() - timedelta(hours=3)},
            {'symbol': 'BTCUSDT', 'pnl': -120, 'volume': 4500, 'fees': 2.8, 'timestamp': datetime.now() - timedelta(hours=2)},
            {'symbol': 'BTCUSDT', 'pnl': -90, 'volume': 3500, 'fees': 2.2, 'timestamp': datetime.now() - timedelta(hours=1)},
        ]
        
        for trade in trades:
            self.performance.add_trade(trade)
            
            # Update risk manager
            is_win = trade['pnl'] > 0
            self.risk_manager.update_trade_result(trade['pnl'], is_win)
        
        print(f"   ✅ Processed {len(trades)} trades")
        
        # Calculate current risk score
        print("\n2️⃣ Calculating Risk Score...")
        
        # Simulate open positions
        positions = [
            {'symbol': 'BTCUSDT', 'size': 0.02, 'markPrice': 51000, 'unrealizedPnl': -50},
            {'symbol': 'ETHUSDT', 'size': 0.5, 'markPrice': 3200, 'unrealizedPnl': 30}
        ]
        
        risk_score = self.risk_manager.get_risk_score(self.balance, positions)
        
        print(f"   🎯 Risk Score: {risk_score['risk_score']:.1f}/100")
        print(f"   📊 Risk Level: {risk_score['risk_level']}")
        print(f"   💰 Daily P&L: ${risk_score['daily_pnl']:.2f}")
        print(f"   📈 Consecutive Losses: {risk_score['consecutive_losses']}")
        print(f"   ✅ Can Trade: {risk_score['can_trade']}")
        
        # Check for alerts
        print("\n3️⃣ Checking Alert Conditions...")
        
        # Check risk alerts
        self.alert_system.check_risk_alerts(risk_score)
        
        # Check performance alerts
        perf_metrics = self.performance.calculate_metrics(period_days=7)
        self.alert_system.check_performance_alerts(perf_metrics)
        
        # Check position alerts
        self.alert_system.check_position_alerts(positions)
        
        # Get alert summary
        alert_summary = self.alert_system.get_alert_summary()
        
        print(f"   🔔 Total Alerts: {alert_summary['total_alerts']}")
        print(f"   ⚠️ Unread Alerts: {alert_summary['unread_alerts']}")
        print(f"   📊 By Priority: {alert_summary['by_priority']}")
        
        # Display critical alerts
        if alert_summary['critical_alerts']:
            print("\n   🚨 CRITICAL ALERTS:")
            for alert in alert_summary['critical_alerts'][:3]:
                print(f"      - {alert['title']}: {alert['message']}")
        
        return risk_score, alert_summary
    
    def test_full_trading_cycle(self):
        """Test complete trading cycle"""
        print_header("FULL TRADING CYCLE SIMULATION")
        
        print("\n🔄 Starting Complete Trading Cycle...\n")
        
        # Step 1: Market Analysis
        print("1️⃣ MARKET ANALYSIS")
        latest_price = self.market_data['close'].iloc[-1]
        price_change_24h = (latest_price - self.market_data['close'].iloc[-24]) / self.market_data['close'].iloc[-24]
        volume_24h = self.market_data['volume'].iloc[-24:].sum()
        
        print(f"   Current Price: ${latest_price:.2f}")
        print(f"   24h Change: {price_change_24h*100:.2f}%")
        print(f"   24h Volume: ${volume_24h:,.0f}")
        
        # Step 2: Strategy Signals
        print("\n2️⃣ STRATEGY SIGNALS")
        
        # Get RSI signal
        rsi_strategy = RSIStrategy('BTCUSDT')
        rsi_signal, rsi_confidence, _ = rsi_strategy.analyze({
            'klines': self.market_data.iloc[-100:].to_dict('records')
        })
        print(f"   RSI Signal: {rsi_signal} (Confidence: {rsi_confidence*100:.1f}%)")
        
        # Get MA signal
        ma_strategy = MovingAverageStrategy('BTCUSDT')
        ma_signal, ma_confidence, _ = ma_strategy.analyze({
            'klines': self.market_data.iloc[-100:].to_dict('records')
        })
        print(f"   MA Signal: {ma_signal} (Confidence: {ma_confidence*100:.1f}%)")
        
        # Step 3: ML Prediction
        print("\n3️⃣ ML PREDICTION")
        ml_prediction = self.ml_predictor.predict(self.market_data)
        print(f"   ML Signal: {ml_prediction['signal']}")
        print(f"   Predicted Change: {ml_prediction['predicted_change']*100:.3f}%")
        
        # Step 4: Risk Assessment
        print("\n4️⃣ RISK ASSESSMENT")
        
        # Consensus decision
        signals = [rsi_signal, ma_signal, ml_prediction['signal']]
        buy_votes = signals.count('BUY')
        sell_votes = signals.count('SELL')
        
        if buy_votes > sell_votes and buy_votes >= 2:
            final_signal = 'BUY'
        elif sell_votes > buy_votes and sell_votes >= 2:
            final_signal = 'SELL'
        else:
            final_signal = 'HOLD'
        
        print(f"   Consensus Signal: {final_signal}")
        print(f"   Votes: BUY={buy_votes}, SELL={sell_votes}, HOLD={3-buy_votes-sell_votes}")
        
        # Step 5: Position Sizing
        if final_signal != 'HOLD':
            print("\n5️⃣ POSITION SIZING")
            
            entry_price = latest_price
            stop_loss = entry_price * 0.98 if final_signal == 'BUY' else entry_price * 1.02
            take_profit = entry_price * 1.04 if final_signal == 'BUY' else entry_price * 0.96
            
            position_size, risk_metrics = self.risk_manager.calculate_position_size(
                self.balance, entry_price, stop_loss, leverage=5
            )
            
            print(f"   Entry Price: ${entry_price:.2f}")
            print(f"   Stop Loss: ${stop_loss:.2f}")
            print(f"   Take Profit: ${take_profit:.2f}")
            print(f"   Position Size: {position_size:.4f} BTC")
            print(f"   Risk Amount: ${risk_metrics['risk_amount']:.2f}")
            
            # Validate trade
            is_valid, reason = self.risk_manager.validate_trade(
                self.balance, [],
                {'size': position_size, 'price': entry_price, 'stop_loss': stop_loss, 'take_profit': take_profit}
            )
            
            print(f"\n   {'✅' if is_valid else '❌'} Trade Validation: {reason}")
        else:
            print("\n5️⃣ No trade - HOLD signal")
        
        print("\n✅ Trading cycle complete!")
    
    def run_all_tests(self):
        """Run all integration tests"""
        print("\n" + "🚀"*30)
        print("  COMPLETE INTEGRATION TEST")
        print("🚀"*30)
        
        # Generate test data
        self.generate_market_data()
        
        # Run tests
        results = []
        
        try:
            # Test 1: ML Prediction Pipeline
            prediction = self.test_ml_prediction_pipeline()
            results.append("✅ ML Prediction Pipeline")
        except Exception as e:
            results.append(f"❌ ML Prediction Pipeline: {str(e)[:50]}")
        
        try:
            # Test 2: Strategy Backtesting
            rsi_result, ma_result = self.test_strategy_backtest()
            results.append("✅ Strategy Backtesting")
        except Exception as e:
            results.append(f"❌ Strategy Backtesting: {str(e)[:50]}")
        
        try:
            # Test 3: Risk Monitoring
            risk_score, alerts = self.test_risk_monitoring()
            results.append("✅ Risk Monitoring & Alerts")
        except Exception as e:
            results.append(f"❌ Risk Monitoring: {str(e)[:50]}")
        
        try:
            # Test 4: Full Trading Cycle
            self.test_full_trading_cycle()
            results.append("✅ Full Trading Cycle")
        except Exception as e:
            results.append(f"❌ Full Trading Cycle: {str(e)[:50]}")
        
        # Summary
        print_header("INTEGRATION TEST SUMMARY")
        print()
        for result in results:
            print(f"  {result}")
        
        passed = sum(1 for r in results if "✅" in r)
        total = len(results)
        
        print()
        print("="*60)
        if passed == total:
            print(f"  🎉 ALL INTEGRATION TESTS PASSED ({passed}/{total})")
            print("  💪 System is ready for production trading!")
        else:
            print(f"  ⚠️ SOME TESTS FAILED ({passed}/{total})")
            print("  🔧 Please review and fix the issues")
        print("="*60)

def main():
    """Run integration tests"""
    test = IntegrationTest()
    test.run_all_tests()

if __name__ == "__main__":
    main()