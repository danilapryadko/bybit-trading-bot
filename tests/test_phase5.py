#!/usr/bin/env python3
"""
Test script for Phase 5: Portfolio Optimization
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

# Import Phase 5 components
from portfolio.portfolio_manager import PortfolioManager
from portfolio.correlation_analyzer import CorrelationAnalyzer
from portfolio.allocation_optimizer import AllocationOptimizer

def print_header(title):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def generate_test_data(symbols, periods=100):
    """Generate test market data for multiple assets"""
    data = {}
    np.random.seed(42)
    
    for symbol in symbols:
        base_price = np.random.uniform(1000, 50000)
        prices = []
        
        # Generate correlated price movements
        trend = np.random.uniform(-0.001, 0.001)
        
        for i in range(periods):
            volatility = np.random.randn() * 0.01
            base_price *= (1 + trend + volatility)
            prices.append(base_price)
        
        dates = pd.date_range(end=datetime.now(), periods=periods, freq='1H')
        data[symbol] = pd.DataFrame({
            'close': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'volume': np.random.uniform(100000, 1000000, periods)
        }, index=dates)
    
    return data

def test_portfolio_manager():
    """Test Portfolio Manager"""
    print_header("TESTING PORTFOLIO MANAGER")
    
    try:
        # Initialize
        portfolio = PortfolioManager()
        print("✅ Portfolio Manager initialized")
        
        # Add assets
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
        test_data = generate_test_data(symbols)
        
        for symbol in symbols:
            portfolio.add_asset(symbol, test_data[symbol])
        print(f"✅ Added {len(symbols)} assets to portfolio")
        
        # Calculate correlation matrix
        corr_matrix = portfolio.calculate_correlation_matrix()
        print(f"✅ Correlation matrix calculated: {corr_matrix.shape}")
        
        # Optimize portfolio
        print("\n📊 Testing optimization methods:")
        
        methods = ['sharpe', 'min_variance', 'risk_parity']
        results = {}
        
        for method in methods:
            result = portfolio.optimize_portfolio(method=method)
            results[method] = result
            
            print(f"\n  {method.upper()} Optimization:")
            print(f"    Expected Return: {result.get('expected_return', 0)*100:.2f}%")
            print(f"    Risk (Volatility): {result.get('risk', 0)*100:.2f}%")
            print(f"    Sharpe Ratio: {result.get('sharpe_ratio', 0):.2f}")
            
            if 'allocation' in result:
                print("    Allocation:")
                for asset, weight in result['allocation'].items():
                    print(f"      {asset}: {weight*100:.1f}%")
        
        # Calculate VaR
        var_metrics = portfolio.calculate_var(confidence_level=0.95)
        print(f"\n✅ VaR Calculated:")
        print(f"   1-Day VaR (95%): ${var_metrics['var_1d']*10000:.2f}")
        print(f"   1-Week VaR (95%): ${var_metrics['var_1w']*10000:.2f}")
        print(f"   1-Month VaR (95%): ${var_metrics['var_1m']*10000:.2f}")
        
        # Check rebalancing
        current_positions = {
            'BTCUSDT': 30000,
            'ETHUSDT': 25000,
            'BNBUSDT': 25000,
            'SOLUSDT': 20000
        }
        
        rebalance = portfolio.check_rebalance_needed(current_positions)
        print(f"\n✅ Rebalance Check:")
        print(f"   Needed: {rebalance['needed']}")
        print(f"   Reason: {rebalance['reason']}")
        print(f"   Max Deviation: {rebalance['max_deviation']*100:.1f}%")
        
        # Get portfolio summary
        summary = portfolio.get_portfolio_summary()
        print(f"\n✅ Portfolio Summary:")
        print(f"   Assets: {summary['num_assets']}")
        print(f"   Effective Assets: {summary.get('effective_assets', 0):.1f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Portfolio Manager test failed: {e}")
        return False

def test_correlation_analyzer():
    """Test Correlation Analyzer"""
    print_header("TESTING CORRELATION ANALYZER")
    
    try:
        # Initialize
        analyzer = CorrelationAnalyzer()
        print("✅ Correlation Analyzer initialized")
        
        # Generate test data
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        test_data = generate_test_data(symbols)
        
        # Convert to returns
        returns_data = {}
        for symbol in symbols:
            prices = test_data[symbol]['close']
            returns = prices.pct_change().dropna()
            returns_data[symbol] = returns
        
        # Analyze portfolio correlations
        corr_analysis = analyzer.analyze_portfolio_correlations(returns_data)
        print(f"✅ Portfolio Correlation Analysis:")
        print(f"   Average Correlation: {corr_analysis['average_correlation']:.3f}")
        print(f"   Diversification Ratio: {corr_analysis['diversification_ratio']:.2f}")
        print(f"   Effective Assets: {corr_analysis['effective_assets']:.1f}")
        
        # Check for highly correlated pairs
        if corr_analysis['highly_correlated_pairs']:
            print(f"   ⚠️ Highly Correlated Pairs Found:")
            for pair in corr_analysis['highly_correlated_pairs']:
                print(f"      {pair['asset1']}-{pair['asset2']}: {pair['correlation']:.3f}")
        
        # Test correlation stability
        print("\n📊 Testing Correlation Stability:")
        stability = analyzer.analyze_correlation_stability(
            returns_data['BTCUSDT'], 
            returns_data['ETHUSDT']
        )
        print(f"   Stable: {stability['stable']}")
        print(f"   Mean Correlation: {stability['mean_correlation']:.3f}")
        print(f"   Std Deviation: {stability['std_correlation']:.3f}")
        print(f"   Current Correlation: {stability['current_correlation']:.3f}")
        
        # Find hedge opportunities
        hedge_ops = analyzer.find_hedge_opportunities(returns_data)
        print(f"\n✅ Hedge Opportunities: {len(hedge_ops)} found")
        
        # Calculate beta
        beta_analysis = analyzer.calculate_beta(
            returns_data['ETHUSDT'],
            returns_data['BTCUSDT']  # BTC as market
        )
        print(f"\n✅ Beta Analysis (ETH vs BTC):")
        print(f"   Beta: {beta_analysis['beta']:.2f}")
        print(f"   Alpha: {beta_analysis['alpha']*100:.3f}%")
        print(f"   R-squared: {beta_analysis['r_squared']:.3f}")
        
        # Calculate correlation risk
        corr_df = pd.DataFrame(returns_data).corr()
        corr_risk = analyzer.calculate_correlation_risk(corr_df)
        print(f"\n✅ Correlation Risk Metrics:")
        print(f"   Average Correlation: {corr_risk['average_correlation']:.3f}")
        print(f"   Systemic Risk Score: {corr_risk['systemic_risk_score']:.3f}")
        print(f"   Diversification Quality: {corr_risk['diversification_quality']:.3f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Correlation Analyzer test failed: {e}")
        return False

def test_allocation_optimizer():
    """Test Allocation Optimizer"""
    print_header("TESTING ALLOCATION OPTIMIZER")
    
    try:
        # Initialize
        optimizer = AllocationOptimizer()
        print("✅ Allocation Optimizer initialized")
        
        # Generate test data
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT']
        test_data = generate_test_data(symbols, periods=200)
        
        # Detect market regime
        market_data = test_data['BTCUSDT']
        regime = optimizer.detect_market_regime(market_data)
        print(f"✅ Market Regime Detected: {regime}")
        
        # Prepare assets for optimization
        assets = []
        for symbol in symbols:
            prices = test_data[symbol]['close']
            returns = prices.pct_change().dropna()
            assets.append({
                'symbol': symbol,
                'returns': returns
            })
        
        # Test different optimization methods
        print("\n📊 Testing Optimization Methods:")
        
        methods = ['max_sharpe', 'min_volatility', 'max_return', 'risk_parity']
        
        for method in methods:
            allocation = optimizer.optimize_allocation(assets, method=method)
            
            print(f"\n  {method.upper()}:")
            print(f"    Expected Return: {allocation['expected_return']*100:.2f}%")
            print(f"    Expected Volatility: {allocation['expected_volatility']*100:.2f}%")
            print(f"    Sharpe Ratio: {allocation['sharpe_ratio']:.2f}")
            print(f"    Weights:")
            for symbol, weight in allocation['weights'].items():
                print(f"      {symbol}: {weight*100:.1f}%")
        
        # Calculate rebalancing trades
        current_values = {
            'BTCUSDT': 25000,
            'ETHUSDT': 20000,
            'BNBUSDT': 20000,
            'SOLUSDT': 20000,
            'ADAUSDT': 15000
        }
        
        target_allocation = allocation['weights']
        trades = optimizer.calculate_rebalancing_trades(current_values, target_allocation)
        
        print(f"\n✅ Rebalancing Trades:")
        print(f"   Total Trades: {trades['total_trades']}")
        print(f"   Transaction Cost: ${trades['transaction_cost']:.2f}")
        print(f"   Cost Percentage: {trades['cost_percentage']:.2f}%")
        
        if trades['trades']:
            print("   Required Trades:")
            for symbol, trade in trades['trades'].items():
                print(f"      {symbol}: {trade['trade_type']} ${abs(trade['trade_value']):.2f}")
        
        # Evaluate allocation performance
        returns_data = {symbol: asset['returns'] for symbol, asset in zip(symbols, assets)}
        performance = optimizer.evaluate_allocation(target_allocation, returns_data)
        
        print(f"\n✅ Allocation Performance:")
        print(f"   Annual Return: {performance['annual_return']*100:.2f}%")
        print(f"   Annual Volatility: {performance['annual_volatility']*100:.2f}%")
        print(f"   Sharpe Ratio: {performance['sharpe_ratio']:.2f}")
        print(f"   Sortino Ratio: {performance['sortino_ratio']:.2f}")
        print(f"   Max Drawdown: {performance['max_drawdown']*100:.2f}%")
        print(f"   Calmar Ratio: {performance['calmar_ratio']:.2f}")
        print(f"   Win Rate: {performance['win_rate']*100:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Allocation Optimizer test failed: {e}")
        return False

def test_integration():
    """Test integration of all Phase 5 components"""
    print_header("INTEGRATION TEST")
    
    try:
        # Initialize all components
        portfolio = PortfolioManager()
        correlation = CorrelationAnalyzer()
        optimizer = AllocationOptimizer()
        
        print("✅ All components initialized")
        
        # Create comprehensive test scenario
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
        test_data = generate_test_data(symbols, periods=250)
        
        # Add assets to portfolio
        for symbol in symbols:
            portfolio.add_asset(symbol, test_data[symbol])
        
        # Detect market regime
        regime = optimizer.detect_market_regime(test_data['BTCUSDT'])
        print(f"📊 Market Regime: {regime}")
        
        # Optimize portfolio based on regime
        if regime == 'bull':
            method = 'max_return'
        elif regime == 'bear':
            method = 'min_volatility'
        else:
            method = 'sharpe'
        
        print(f"📊 Using {method} optimization for {regime} market")
        
        result = portfolio.optimize_portfolio(method=method)
        print(f"✅ Portfolio Optimized:")
        print(f"   Expected Return: {result.get('expected_return', 0)*100:.2f}%")
        print(f"   Risk: {result.get('risk', 0)*100:.2f}%")
        print(f"   Sharpe Ratio: {result.get('sharpe_ratio', 0):.2f}")
        
        # Analyze correlations
        returns_data = {}
        for symbol in symbols:
            prices = test_data[symbol]['close']
            returns = prices.pct_change().dropna()
            returns_data[symbol] = returns
        
        corr_analysis = correlation.analyze_portfolio_correlations(returns_data)
        print(f"\n✅ Correlation Analysis:")
        print(f"   Average Correlation: {corr_analysis['average_correlation']:.3f}")
        print(f"   Effective Assets: {corr_analysis['effective_assets']:.1f}")
        
        # Risk assessment
        var_metrics = portfolio.calculate_var()
        contributions = portfolio.analyze_asset_contribution()
        
        print(f"\n✅ Risk Assessment:")
        print(f"   1-Day VaR: ${var_metrics['var_1d']*100000:.2f}")
        print(f"   Asset Contributions:")
        for symbol, contrib in contributions.items():
            print(f"      {symbol}: Risk {contrib['risk_contribution']*100:.1f}%, Return {contrib['return_contribution']*100:.1f}%")
        
        # Final portfolio summary
        summary = portfolio.get_portfolio_summary()
        print(f"\n✅ Final Portfolio Summary:")
        print(f"   Number of Assets: {summary['num_assets']}")
        print(f"   Optimization Complete: {'optimal_weights' in summary and summary['optimal_weights'] is not None}")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def main():
    """Run all Phase 5 tests"""
    print("\n" + "🚀"*30)
    print("  PHASE 5 TEST SUITE: PORTFOLIO OPTIMIZATION")
    print("🚀"*30)
    
    results = []
    
    # Test Portfolio Manager
    test_name = "Portfolio Manager"
    print(f"\n🔬 Testing {test_name}...")
    if test_portfolio_manager():
        results.append(f"✅ {test_name}")
    else:
        results.append(f"❌ {test_name}")
    
    # Test Correlation Analyzer
    test_name = "Correlation Analyzer"
    print(f"\n🔬 Testing {test_name}...")
    if test_correlation_analyzer():
        results.append(f"✅ {test_name}")
    else:
        results.append(f"❌ {test_name}")
    
    # Test Allocation Optimizer
    test_name = "Allocation Optimizer"
    print(f"\n🔬 Testing {test_name}...")
    if test_allocation_optimizer():
        results.append(f"✅ {test_name}")
    else:
        results.append(f"❌ {test_name}")
    
    # Test Integration
    test_name = "Integration"
    print(f"\n🔬 Testing {test_name}...")
    if test_integration():
        results.append(f"✅ {test_name}")
    else:
        results.append(f"❌ {test_name}")
    
    # Print summary
    print_header("TEST SUMMARY")
    for result in results:
        print(f"  {result}")
    
    passed = sum(1 for r in results if "✅" in r)
    total = len(results)
    
    print("\n" + "="*60)
    if passed == total:
        print(f"  🎉 ALL TESTS PASSED ({passed}/{total})")
        print("  ✨ Phase 5 is ready for deployment!")
    else:
        print(f"  ⚠️ SOME TESTS FAILED ({passed}/{total})")
        print("  🔧 Please review and fix the issues")
    print("="*60)

if __name__ == "__main__":
    main()