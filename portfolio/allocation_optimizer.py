"""
Dynamic Asset Allocation Optimizer
Optimizes portfolio allocation based on market conditions
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from scipy.optimize import minimize, differential_evolution
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class AllocationOptimizer:
    """Advanced portfolio allocation optimization"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.current_allocation = {}
        self.target_allocation = {}
        self.constraints = {}
        
        # Optimization parameters
        self.risk_free_rate = self.config.get('risk_free_rate', 0.02)  # 2% annual
        self.target_volatility = self.config.get('target_volatility', 0.15)  # 15%
        self.max_drawdown = self.config.get('max_drawdown', 0.20)  # 20%
        self.min_weight = self.config.get('min_weight', 0.00)  # 0% minimum
        self.max_weight = self.config.get('max_weight', 0.40)  # 40% maximum
        self.transaction_cost = self.config.get('transaction_cost', 0.001)  # 0.1%
        
        # Regime detection
        self.regime = 'neutral'
        self.regime_allocations = {
            'bull': {'risk_assets': 0.8, 'safe_assets': 0.2},
            'bear': {'risk_assets': 0.3, 'safe_assets': 0.7},
            'neutral': {'risk_assets': 0.6, 'safe_assets': 0.4}
        }
        
    def detect_market_regime(self, market_data: pd.DataFrame) -> str:
        """
        Detect current market regime
        
        Args:
            market_data: Market price data
            
        Returns:
            Market regime ('bull', 'bear', 'neutral')
        """
        if len(market_data) < 50:
            return 'neutral'
        
        # Calculate indicators
        sma_20 = market_data['close'].rolling(20).mean()
        sma_50 = market_data['close'].rolling(50).mean()
        
        # Recent price action
        current_price = market_data['close'].iloc[-1]
        
        # Trend strength
        if current_price > sma_20.iloc[-1] and sma_20.iloc[-1] > sma_50.iloc[-1]:
            trend_score = 1  # Bullish
        elif current_price < sma_20.iloc[-1] and sma_20.iloc[-1] < sma_50.iloc[-1]:
            trend_score = -1  # Bearish
        else:
            trend_score = 0  # Neutral
        
        # Volatility analysis
        returns = market_data['close'].pct_change()
        recent_vol = returns.iloc[-20:].std()
        historical_vol = returns.std()
        vol_ratio = recent_vol / historical_vol if historical_vol > 0 else 1
        
        # Momentum
        momentum_10 = (current_price - market_data['close'].iloc[-10]) / market_data['close'].iloc[-10]
        momentum_30 = (current_price - market_data['close'].iloc[-30]) / market_data['close'].iloc[-30]
        
        # Determine regime
        if trend_score > 0 and momentum_10 > 0.05 and vol_ratio < 1.5:
            self.regime = 'bull'
        elif trend_score < 0 and momentum_10 < -0.05 and vol_ratio > 1.2:
            self.regime = 'bear'
        else:
            self.regime = 'neutral'
        
        logger.info(f"Market regime detected: {self.regime}")
        return self.regime
    
    def optimize_allocation(self, assets: List[Dict[str, Any]], 
                          method: str = 'max_sharpe') -> Dict[str, Any]:
        """
        Optimize asset allocation
        
        Args:
            assets: List of asset dictionaries with returns data
            method: Optimization method
            
        Returns:
            Optimal allocation
        """
        if not assets:
            return {}
        
        # Prepare returns matrix
        returns_data = {}
        for asset in assets:
            symbol = asset['symbol']
            returns = asset.get('returns', pd.Series())
            if not returns.empty:
                returns_data[symbol] = returns
        
        if not returns_data:
            return {}
        
        returns_df = pd.DataFrame(returns_data).dropna()
        n_assets = len(returns_data)
        
        # Calculate expected returns and covariance
        expected_returns = returns_df.mean() * 252  # Annualized
        cov_matrix = returns_df.cov() * 252  # Annualized
        
        # Initial weights
        init_weights = np.array([1/n_assets] * n_assets)
        
        # Optimization method
        if method == 'max_sharpe':
            result = self._optimize_max_sharpe(expected_returns, cov_matrix, init_weights)
        elif method == 'min_volatility':
            result = self._optimize_min_volatility(expected_returns, cov_matrix, init_weights)
        elif method == 'max_return':
            result = self._optimize_max_return(expected_returns, cov_matrix, init_weights)
        elif method == 'risk_parity':
            result = self._optimize_risk_parity(expected_returns, cov_matrix, init_weights)
        elif method == 'black_litterman':
            result = self._black_litterman_optimization(expected_returns, cov_matrix, init_weights)
        else:
            raise ValueError(f"Unknown optimization method: {method}")
        
        # Create allocation dictionary
        symbols = list(returns_data.keys())
        allocation = {
            'weights': {symbol: float(weight) for symbol, weight in zip(symbols, result['weights'])},
            'expected_return': float(result['expected_return']),
            'expected_volatility': float(result['expected_volatility']),
            'sharpe_ratio': float(result['sharpe_ratio']),
            'method': method,
            'regime': self.regime
        }
        
        self.target_allocation = allocation['weights']
        return allocation
    
    def _optimize_max_sharpe(self, expected_returns: pd.Series, 
                            cov_matrix: pd.DataFrame, 
                            init_weights: np.ndarray) -> Dict[str, Any]:
        """Maximize Sharpe ratio"""
        n_assets = len(expected_returns)
        
        def negative_sharpe(weights):
            portfolio_return = np.sum(weights * expected_returns)
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            sharpe = (portfolio_return - self.risk_free_rate) / portfolio_vol
            return -sharpe
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
        ]
        
        # Bounds
        bounds = tuple((self.min_weight, self.max_weight) for _ in range(n_assets))
        
        # Optimize
        result = minimize(negative_sharpe, init_weights, method='SLSQP',
                         bounds=bounds, constraints=constraints)
        
        # Calculate metrics
        portfolio_return = np.sum(result.x * expected_returns)
        portfolio_vol = np.sqrt(np.dot(result.x.T, np.dot(cov_matrix, result.x)))
        sharpe = (portfolio_return - self.risk_free_rate) / portfolio_vol
        
        return {
            'weights': result.x,
            'expected_return': portfolio_return,
            'expected_volatility': portfolio_vol,
            'sharpe_ratio': sharpe
        }
    
    def _optimize_min_volatility(self, expected_returns: pd.Series,
                                cov_matrix: pd.DataFrame,
                                init_weights: np.ndarray) -> Dict[str, Any]:
        """Minimize portfolio volatility"""
        n_assets = len(expected_returns)
        
        def portfolio_volatility(weights):
            return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
        ]
        
        # Add minimum return constraint
        min_return = expected_returns.min() * 0.5  # At least 50% of minimum asset return
        constraints.append({
            'type': 'ineq',
            'fun': lambda x: np.sum(x * expected_returns) - min_return
        })
        
        # Bounds
        bounds = tuple((self.min_weight, self.max_weight) for _ in range(n_assets))
        
        # Optimize
        result = minimize(portfolio_volatility, init_weights, method='SLSQP',
                         bounds=bounds, constraints=constraints)
        
        # Calculate metrics
        portfolio_return = np.sum(result.x * expected_returns)
        portfolio_vol = portfolio_volatility(result.x)
        sharpe = (portfolio_return - self.risk_free_rate) / portfolio_vol
        
        return {
            'weights': result.x,
            'expected_return': portfolio_return,
            'expected_volatility': portfolio_vol,
            'sharpe_ratio': sharpe
        }
    
    def _optimize_max_return(self, expected_returns: pd.Series,
                            cov_matrix: pd.DataFrame,
                            init_weights: np.ndarray) -> Dict[str, Any]:
        """Maximize expected return with volatility constraint"""
        n_assets = len(expected_returns)
        
        def negative_return(weights):
            return -np.sum(weights * expected_returns)
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
            # Volatility constraint
            {'type': 'ineq', 
             'fun': lambda x: self.target_volatility - np.sqrt(np.dot(x.T, np.dot(cov_matrix, x)))}
        ]
        
        # Bounds
        bounds = tuple((self.min_weight, self.max_weight) for _ in range(n_assets))
        
        # Optimize
        result = minimize(negative_return, init_weights, method='SLSQP',
                         bounds=bounds, constraints=constraints)
        
        # Calculate metrics
        portfolio_return = np.sum(result.x * expected_returns)
        portfolio_vol = np.sqrt(np.dot(result.x.T, np.dot(cov_matrix, result.x)))
        sharpe = (portfolio_return - self.risk_free_rate) / portfolio_vol
        
        return {
            'weights': result.x,
            'expected_return': portfolio_return,
            'expected_volatility': portfolio_vol,
            'sharpe_ratio': sharpe
        }
    
    def _optimize_risk_parity(self, expected_returns: pd.Series,
                             cov_matrix: pd.DataFrame,
                             init_weights: np.ndarray) -> Dict[str, Any]:
        """Equal risk contribution optimization"""
        n_assets = len(expected_returns)
        
        def risk_budget_objective(weights):
            # Calculate portfolio volatility
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            
            # Marginal risk contribution
            marginal_contrib = np.dot(cov_matrix, weights) / portfolio_vol
            
            # Risk contribution of each asset
            contrib = weights * marginal_contrib
            
            # Target equal contribution
            target_contrib = np.ones(n_assets) / n_assets
            
            # Minimize squared deviations
            return np.sum((contrib / np.sum(contrib) - target_contrib) ** 2)
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
        ]
        
        # Bounds (no short selling for risk parity)
        bounds = tuple((0.001, self.max_weight) for _ in range(n_assets))
        
        # Optimize
        result = minimize(risk_budget_objective, init_weights, method='SLSQP',
                         bounds=bounds, constraints=constraints)
        
        # Calculate metrics
        portfolio_return = np.sum(result.x * expected_returns)
        portfolio_vol = np.sqrt(np.dot(result.x.T, np.dot(cov_matrix, result.x)))
        sharpe = (portfolio_return - self.risk_free_rate) / portfolio_vol
        
        return {
            'weights': result.x,
            'expected_return': portfolio_return,
            'expected_volatility': portfolio_vol,
            'sharpe_ratio': sharpe
        }
    
    def _black_litterman_optimization(self, expected_returns: pd.Series,
                                     cov_matrix: pd.DataFrame,
                                     init_weights: np.ndarray,
                                     views: Optional[Dict] = None) -> Dict[str, Any]:
        """Black-Litterman model optimization"""
        n_assets = len(expected_returns)
        
        # Market equilibrium weights (equal weight for simplicity)
        market_weights = np.ones(n_assets) / n_assets
        
        # Risk aversion parameter
        delta = 2.5
        
        # Equilibrium returns
        pi = delta * np.dot(cov_matrix, market_weights)
        
        # If no views provided, use equilibrium returns
        if views is None:
            posterior_returns = pi
        else:
            # Implement Black-Litterman with views
            # This is simplified - full implementation would include P, Q, Omega matrices
            tau = 0.025
            posterior_cov = np.linalg.inv(np.linalg.inv(tau * cov_matrix) + np.linalg.inv(cov_matrix))
            posterior_returns = np.dot(posterior_cov, 
                                      np.dot(np.linalg.inv(tau * cov_matrix), pi) + 
                                      np.dot(np.linalg.inv(cov_matrix), expected_returns))
        
        # Optimize with posterior returns
        def negative_utility(weights):
            portfolio_return = np.sum(weights * posterior_returns)
            portfolio_var = np.dot(weights.T, np.dot(cov_matrix, weights))
            utility = portfolio_return - (delta / 2) * portfolio_var
            return -utility
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
        ]
        
        # Bounds
        bounds = tuple((self.min_weight, self.max_weight) for _ in range(n_assets))
        
        # Optimize
        result = minimize(negative_utility, init_weights, method='SLSQP',
                         bounds=bounds, constraints=constraints)
        
        # Calculate metrics
        portfolio_return = np.sum(result.x * expected_returns)
        portfolio_vol = np.sqrt(np.dot(result.x.T, np.dot(cov_matrix, result.x)))
        sharpe = (portfolio_return - self.risk_free_rate) / portfolio_vol
        
        return {
            'weights': result.x,
            'expected_return': portfolio_return,
            'expected_volatility': portfolio_vol,
            'sharpe_ratio': sharpe
        }
    
    def calculate_rebalancing_trades(self, current_values: Dict[str, float],
                                    target_allocation: Dict[str, float]) -> Dict[str, Any]:
        """
        Calculate trades needed for rebalancing
        
        Args:
            current_values: Current position values by symbol
            target_allocation: Target allocation weights
            
        Returns:
            Rebalancing trades
        """
        total_value = sum(current_values.values())
        
        if total_value == 0:
            return {'trades': {}, 'total_trades': 0, 'transaction_cost': 0}
        
        trades = {}
        total_transaction_cost = 0
        
        for symbol, target_weight in target_allocation.items():
            current_value = current_values.get(symbol, 0)
            current_weight = current_value / total_value
            target_value = target_weight * total_value
            
            trade_value = target_value - current_value
            
            # Only trade if difference is significant (>1% of portfolio)
            if abs(trade_value) > total_value * 0.01:
                trades[symbol] = {
                    'current_value': current_value,
                    'current_weight': current_weight,
                    'target_value': target_value,
                    'target_weight': target_weight,
                    'trade_value': trade_value,
                    'trade_type': 'BUY' if trade_value > 0 else 'SELL',
                    'trade_cost': abs(trade_value) * self.transaction_cost
                }
                total_transaction_cost += abs(trade_value) * self.transaction_cost
        
        return {
            'trades': trades,
            'total_trades': len(trades),
            'transaction_cost': total_transaction_cost,
            'cost_percentage': (total_transaction_cost / total_value) * 100 if total_value > 0 else 0
        }
    
    def evaluate_allocation(self, weights: Dict[str, float],
                          returns_data: Dict[str, pd.Series]) -> Dict[str, Any]:
        """
        Evaluate allocation performance
        
        Args:
            weights: Portfolio weights
            returns_data: Historical returns by symbol
            
        Returns:
            Performance metrics
        """
        # Create returns DataFrame
        returns_df = pd.DataFrame(returns_data).dropna()
        
        # Convert weights to array
        weight_array = np.array([weights.get(symbol, 0) for symbol in returns_df.columns])
        
        # Calculate portfolio returns
        portfolio_returns = returns_df.dot(weight_array)
        
        # Performance metrics
        annual_return = portfolio_returns.mean() * 252
        annual_vol = portfolio_returns.std() * np.sqrt(252)
        sharpe_ratio = (annual_return - self.risk_free_rate) / annual_vol if annual_vol > 0 else 0
        
        # Downside risk
        downside_returns = portfolio_returns[portfolio_returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        sortino_ratio = (annual_return - self.risk_free_rate) / downside_deviation if downside_deviation > 0 else 0
        
        # Maximum drawdown
        cumulative_returns = (1 + portfolio_returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Calmar ratio
        calmar_ratio = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        return {
            'annual_return': float(annual_return),
            'annual_volatility': float(annual_vol),
            'sharpe_ratio': float(sharpe_ratio),
            'sortino_ratio': float(sortino_ratio),
            'max_drawdown': float(max_drawdown),
            'calmar_ratio': float(calmar_ratio),
            'win_rate': float((portfolio_returns > 0).mean()),
            'best_day': float(portfolio_returns.max()),
            'worst_day': float(portfolio_returns.min()),
            'skewness': float(portfolio_returns.skew()),
            'kurtosis': float(portfolio_returns.kurtosis())
        }