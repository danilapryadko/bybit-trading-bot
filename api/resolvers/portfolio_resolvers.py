"""
GraphQL resolvers for portfolio management
"""

import logging
import json
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timedelta

from portfolio.portfolio_manager import PortfolioManager
from portfolio.correlation_analyzer import CorrelationAnalyzer
from portfolio.allocation_optimizer import AllocationOptimizer
from data_feed.market_data import MarketDataFeed

logger = logging.getLogger(__name__)

# Initialize components
portfolio_manager = PortfolioManager()
correlation_analyzer = CorrelationAnalyzer()
allocation_optimizer = AllocationOptimizer()
market_data_feed = MarketDataFeed()

# Query Resolvers
async def get_portfolio_summary(parent, info):
    """Get portfolio summary metrics"""
    try:
        summary = portfolio_manager.get_portfolio_summary()
        
        # Calculate current metrics
        var_metrics = summary.get('var_metrics', {})
        expected_metrics = summary.get('expected_metrics', {})
        
        return {
            'totalValue': 100000,  # Placeholder - would come from positions
            'dailyReturn': 0.02,  # Placeholder
            'totalReturn': 0.15,  # Placeholder
            'volatility': expected_metrics.get('annual_volatility', 0),
            'sharpeRatio': expected_metrics.get('sharpe_ratio', 0),
            'sortinoRatio': 1.8,  # Placeholder
            'maxDrawdown': 0.08,  # Placeholder
            'calmarRatio': 1.5,  # Placeholder
            'var95': var_metrics.get('var_1d', 0),
            'effectiveAssets': summary.get('effective_assets', len(summary.get('assets', [])))
        }
    except Exception as e:
        logger.error(f"Error getting portfolio summary: {e}")
        return {
            'totalValue': 0,
            'dailyReturn': 0,
            'totalReturn': 0,
            'volatility': 0,
            'sharpeRatio': 0,
            'sortinoRatio': 0,
            'maxDrawdown': 0,
            'calmarRatio': 0,
            'var95': 0,
            'effectiveAssets': 0
        }

async def get_portfolio_assets(parent, info):
    """Get portfolio assets"""
    try:
        assets = portfolio_manager.assets
        weights = portfolio_manager.optimal_weights if portfolio_manager.optimal_weights is not None else []
        
        portfolio_assets = []
        for i, symbol in enumerate(assets):
            weight = weights[i] if i < len(weights) else 0
            portfolio_assets.append({
                'symbol': symbol,
                'weight': weight,
                'value': weight * 100000,  # Placeholder total value
                'returns': 0.05,  # Placeholder returns
                'risk': 0.15  # Placeholder risk
            })
        
        return portfolio_assets
    except Exception as e:
        logger.error(f"Error getting portfolio assets: {e}")
        return []

async def optimize_portfolio(parent, info, method='sharpe', assets=None):
    """Optimize portfolio allocation"""
    try:
        # Get market data for assets
        if not assets:
            assets = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        
        # Add assets to portfolio manager
        for symbol in assets:
            # Get historical data (placeholder - would fetch real data)
            data = pd.DataFrame({
                'close': pd.Series(range(100, 200))
            })
            portfolio_manager.add_asset(symbol, data)
        
        # Optimize
        result = portfolio_manager.optimize_portfolio(method=method)
        
        return {
            'weights': result.get('allocation', {}),
            'expectedReturn': result.get('expected_return', 0),
            'expectedVolatility': result.get('risk', 0),
            'sharpeRatio': result.get('sharpe_ratio', 0),
            'method': method,
            'regime': allocation_optimizer.regime,
            'success': result.get('success', True)
        }
    except Exception as e:
        logger.error(f"Error optimizing portfolio: {e}")
        return {
            'weights': {},
            'expectedReturn': 0,
            'expectedVolatility': 0,
            'sharpeRatio': 0,
            'method': method,
            'regime': 'neutral',
            'success': False
        }

async def get_correlation_matrix(parent, info, assets=None):
    """Get correlation matrix for assets"""
    try:
        if not assets:
            assets = portfolio_manager.assets
        
        # Calculate correlation matrix
        correlation_matrix = portfolio_manager.calculate_correlation_matrix()
        
        if correlation_matrix.empty:
            return {
                'matrix': {},
                'averageCorrelation': 0,
                'maxCorrelation': 0,
                'minCorrelation': 0,
                'highlyCorrelated': []
            }
        
        # Find highly correlated pairs
        highly_correlated = []
        for i in range(len(assets)):
            for j in range(i + 1, len(assets)):
                corr = correlation_matrix.iloc[i, j]
                if abs(corr) > 0.7:
                    highly_correlated.append({
                        'asset1': assets[i],
                        'asset2': assets[j],
                        'correlation': corr,
                        'pValue': 0.01,  # Placeholder
                        'stable': True  # Placeholder
                    })
        
        # Calculate statistics
        upper_triangle = correlation_matrix.values[pd.np.triu_indices_from(correlation_matrix.values, k=1)]
        
        return {
            'matrix': correlation_matrix.to_dict(),
            'averageCorrelation': upper_triangle.mean() if len(upper_triangle) > 0 else 0,
            'maxCorrelation': upper_triangle.max() if len(upper_triangle) > 0 else 0,
            'minCorrelation': upper_triangle.min() if len(upper_triangle) > 0 else 0,
            'highlyCorrelated': highly_correlated
        }
    except Exception as e:
        logger.error(f"Error getting correlation matrix: {e}")
        return {
            'matrix': {},
            'averageCorrelation': 0,
            'maxCorrelation': 0,
            'minCorrelation': 0,
            'highlyCorrelated': []
        }

async def check_rebalance_needed(parent, info):
    """Check if portfolio rebalancing is needed"""
    try:
        # Get current positions (placeholder)
        current_positions = {
            'BTCUSDT': 40000,
            'ETHUSDT': 35000,
            'BNBUSDT': 25000
        }
        
        result = portfolio_manager.check_rebalance_needed(current_positions)
        
        # Convert trades to list format
        trades = []
        for symbol, trade_info in result.get('trades_required', {}).items():
            trades.append({
                'symbol': symbol,
                'currentValue': trade_info['current_value'],
                'targetValue': trade_info['target_value'],
                'tradeValue': trade_info['trade_value'],
                'tradeType': trade_info['action'],
                'tradeCost': trade_info.get('trade_cost', 0)
            })
        
        return {
            'needed': result.get('needed', False),
            'reason': result.get('reason', ''),
            'maxDeviation': result.get('max_deviation', 0),
            'trades': trades,
            'transactionCost': sum(t['tradeCost'] for t in trades)
        }
    except Exception as e:
        logger.error(f"Error checking rebalance: {e}")
        return {
            'needed': False,
            'reason': str(e),
            'maxDeviation': 0,
            'trades': [],
            'transactionCost': 0
        }

async def get_portfolio_var(parent, info, confidence=0.95):
    """Get portfolio Value at Risk"""
    try:
        var_metrics = portfolio_manager.calculate_var(confidence_level=confidence)
        return var_metrics
    except Exception as e:
        logger.error(f"Error calculating VaR: {e}")
        return {
            'var_1d': 0,
            'var_1w': 0,
            'var_1m': 0,
            'parametric_var_1d': 0,
            'confidence_level': confidence
        }

async def get_asset_contributions(parent, info):
    """Get asset contributions to portfolio risk and return"""
    try:
        contributions = portfolio_manager.analyze_asset_contribution()
        
        result = []
        for symbol, contrib in contributions.items():
            result.append({
                'symbol': symbol,
                'weight': contrib['weight'],
                'returnContribution': contrib['return_contribution'],
                'riskContribution': contrib['risk_contribution'],
                'expectedReturn': contrib['expected_return'],
                'standaloneRisk': contrib['standalone_risk']
            })
        
        return result
    except Exception as e:
        logger.error(f"Error getting asset contributions: {e}")
        return []

async def detect_market_regime(parent, info):
    """Detect current market regime"""
    try:
        # Get market data (placeholder - would fetch real data)
        market_data = pd.DataFrame({
            'close': pd.Series(range(100, 200)),
            'high': pd.Series(range(102, 202)),
            'low': pd.Series(range(98, 198)),
            'volume': pd.Series([1000000] * 100)
        })
        
        regime = allocation_optimizer.detect_market_regime(market_data)
        
        return {
            'regime': regime,
            'confidence': 0.75,  # Placeholder confidence
            'indicators': {
                'trend': 'up',
                'volatility': 'normal',
                'momentum': 'positive'
            },
            'allocation': allocation_optimizer.regime_allocations[regime]
        }
    except Exception as e:
        logger.error(f"Error detecting market regime: {e}")
        return {
            'regime': 'neutral',
            'confidence': 0,
            'indicators': {},
            'allocation': {}
        }

# Mutation Resolvers
async def add_portfolio_asset(parent, info, symbol, allocation):
    """Add asset to portfolio"""
    try:
        # Get market data for asset (placeholder)
        data = pd.DataFrame({
            'close': pd.Series(range(100, 200))
        })
        portfolio_manager.add_asset(symbol, data)
        
        # Update weights if needed
        # This would trigger reoptimization in practice
        
        return True
    except Exception as e:
        logger.error(f"Error adding portfolio asset: {e}")
        return False

async def remove_portfolio_asset(parent, info, symbol):
    """Remove asset from portfolio"""
    try:
        if symbol in portfolio_manager.assets:
            portfolio_manager.assets.remove(symbol)
            # Trigger reoptimization
            return True
        return False
    except Exception as e:
        logger.error(f"Error removing portfolio asset: {e}")
        return False

async def execute_rebalance(parent, info, trades):
    """Execute portfolio rebalancing trades"""
    try:
        # This would execute actual trades through the trading engine
        # For now, just log the trades
        logger.info(f"Executing rebalance trades: {trades}")
        return True
    except Exception as e:
        logger.error(f"Error executing rebalance: {e}")
        return False

async def set_rebalance_threshold(parent, info, threshold):
    """Set rebalancing threshold"""
    try:
        portfolio_manager.rebalance_threshold = threshold
        return True
    except Exception as e:
        logger.error(f"Error setting rebalance threshold: {e}")
        return False

# Export resolvers
portfolio_query_resolvers = {
    'getPortfolioSummary': get_portfolio_summary,
    'getPortfolioAssets': get_portfolio_assets,
    'optimizePortfolio': optimize_portfolio,
    'getCorrelationMatrix': get_correlation_matrix,
    'checkRebalanceNeeded': check_rebalance_needed,
    'getPortfolioVaR': get_portfolio_var,
    'getAssetContributions': get_asset_contributions,
    'detectMarketRegime': detect_market_regime,
}

portfolio_mutation_resolvers = {
    'addPortfolioAsset': add_portfolio_asset,
    'removePortfolioAsset': remove_portfolio_asset,
    'executeRebalance': execute_rebalance,
    'setRebalanceThreshold': set_rebalance_threshold,
}