"""
Portfolio Management System
Handles multi-asset portfolio optimization and allocation
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from scipy.optimize import minimize
from scipy.stats import norm
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class PortfolioManager:
    """Advanced portfolio management and optimization"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.assets = []
        self.positions = {}
        self.historical_data = {}
        self.correlation_matrix = None
        self.optimal_weights = None
        
        # Portfolio parameters
        self.target_return = self.config.get('target_return', 0.15)  # 15% annual
        self.max_risk = self.config.get('max_risk', 0.20)  # 20% volatility
        self.rebalance_threshold = self.config.get('rebalance_threshold', 0.05)  # 5% deviation
        self.min_position_size = self.config.get('min_position_size', 0.01)  # 1% minimum
        self.max_position_size = self.config.get('max_position_size', 0.40)  # 40% maximum
        
        # Risk metrics
        self.confidence_level = self.config.get('confidence_level', 0.95)
        self.lookback_period = self.config.get('lookback_period', 252)  # Trading days
        
    def add_asset(self, symbol: str, data: pd.DataFrame):
        """
        Add asset to portfolio
        
        Args:
            symbol: Asset symbol
            data: Historical price data
        """
        if symbol not in self.assets:
            self.assets.append(symbol)
            
        self.historical_data[symbol] = data
        logger.info(f"Added {symbol} to portfolio")
        
    def calculate_returns(self, prices: pd.DataFrame) -> pd.DataFrame:
        """Calculate returns from price data"""
        returns = prices.pct_change().dropna()
        return returns
    
    def calculate_correlation_matrix(self) -> pd.DataFrame:
        """Calculate correlation matrix for all assets"""
        if len(self.assets) < 2:
            return pd.DataFrame()
        
        # Prepare returns data
        returns_data = {}
        min_length = float('inf')
        
        for symbol in self.assets:
            if symbol in self.historical_data:
                prices = self.historical_data[symbol]['close']
                returns = self.calculate_returns(prices)
                returns_data[symbol] = returns
                min_length = min(min_length, len(returns))
        
        # Align all series to same length
        for symbol in returns_data:
            returns_data[symbol] = returns_data[symbol].iloc[-min_length:]
        
        # Create DataFrame and calculate correlation
        returns_df = pd.DataFrame(returns_data)
        self.correlation_matrix = returns_df.corr()
        
        return self.correlation_matrix
    
    def calculate_portfolio_metrics(self, weights: np.ndarray, 
                                   returns: pd.DataFrame) -> Tuple[float, float]:
        """
        Calculate portfolio return and risk
        
        Args:
            weights: Asset weights
            returns: Returns DataFrame
            
        Returns:
            Tuple of (expected_return, portfolio_risk)
        """
        # Expected return
        mean_returns = returns.mean()
        portfolio_return = np.sum(weights * mean_returns) * 252  # Annualized
        
        # Portfolio risk (volatility)
        cov_matrix = returns.cov() * 252  # Annualized
        portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
        portfolio_risk = np.sqrt(portfolio_variance)
        
        return portfolio_return, portfolio_risk
    
    def optimize_portfolio(self, method: str = 'sharpe') -> Dict[str, Any]:
        """
        Optimize portfolio allocation
        
        Args:
            method: Optimization method ('sharpe', 'min_variance', 'risk_parity')
            
        Returns:
            Optimization results
        """
        logger.info(f"Optimizing portfolio using {method} method")
        
        # Prepare returns data
        returns_data = {}
        for symbol in self.assets:
            if symbol in self.historical_data:
                prices = self.historical_data[symbol]['close']
                returns = self.calculate_returns(prices)
                returns_data[symbol] = returns
        
        if not returns_data:
            logger.warning("No data available for optimization")
            return {}
        
        # Create aligned DataFrame
        returns_df = pd.DataFrame(returns_data).dropna()
        n_assets = len(self.assets)
        
        # Initial weights (equal weight)
        init_weights = np.array([1/n_assets] * n_assets)
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}  # Weights sum to 1
        ]
        
        # Bounds for each weight
        bounds = tuple((self.min_position_size, self.max_position_size) 
                      for _ in range(n_assets))
        
        # Optimization based on method
        if method == 'sharpe':
            result = self._optimize_sharpe_ratio(returns_df, init_weights, 
                                                constraints, bounds)
        elif method == 'min_variance':
            result = self._optimize_min_variance(returns_df, init_weights, 
                                                constraints, bounds)
        elif method == 'risk_parity':
            result = self._optimize_risk_parity(returns_df, init_weights)
        else:
            raise ValueError(f"Unknown optimization method: {method}")
        
        # Store optimal weights
        self.optimal_weights = result['weights']
        
        # Add asset allocation
        result['allocation'] = {
            symbol: weight 
            for symbol, weight in zip(self.assets, self.optimal_weights)
        }
        
        return result
    
    def _optimize_sharpe_ratio(self, returns: pd.DataFrame, init_weights: np.ndarray,
                               constraints: List, bounds: Tuple) -> Dict[str, Any]:
        """Optimize for maximum Sharpe ratio"""
        
        def negative_sharpe(weights):
            ret, risk = self.calculate_portfolio_metrics(weights, returns)
            risk_free_rate = 0.02  # 2% risk-free rate
            sharpe = (ret - risk_free_rate) / risk if risk > 0 else 0
            return -sharpe
        
        # Optimize
        result = minimize(negative_sharpe, init_weights, method='SLSQP',
                         bounds=bounds, constraints=constraints)
        
        # Calculate final metrics
        opt_return, opt_risk = self.calculate_portfolio_metrics(result.x, returns)
        opt_sharpe = (opt_return - 0.02) / opt_risk if opt_risk > 0 else 0
        
        return {
            'weights': result.x,
            'expected_return': opt_return,
            'risk': opt_risk,
            'sharpe_ratio': opt_sharpe,
            'success': result.success
        }
    
    def _optimize_min_variance(self, returns: pd.DataFrame, init_weights: np.ndarray,
                               constraints: List, bounds: Tuple) -> Dict[str, Any]:
        """Optimize for minimum variance"""
        
        def portfolio_variance(weights):
            _, risk = self.calculate_portfolio_metrics(weights, returns)
            return risk
        
        # Optimize
        result = minimize(portfolio_variance, init_weights, method='SLSQP',
                         bounds=bounds, constraints=constraints)
        
        # Calculate final metrics
        opt_return, opt_risk = self.calculate_portfolio_metrics(result.x, returns)
        
        return {
            'weights': result.x,
            'expected_return': opt_return,
            'risk': opt_risk,
            'sharpe_ratio': (opt_return - 0.02) / opt_risk if opt_risk > 0 else 0,
            'success': result.success
        }
    
    def _optimize_risk_parity(self, returns: pd.DataFrame, 
                             init_weights: np.ndarray) -> Dict[str, Any]:
        """Optimize for equal risk contribution"""
        
        cov_matrix = returns.cov() * 252
        
        def risk_contribution_objective(weights):
            # Calculate portfolio risk
            portfolio_var = np.dot(weights.T, np.dot(cov_matrix, weights))
            portfolio_std = np.sqrt(portfolio_var)
            
            # Marginal risk contribution
            marginal_contrib = np.dot(cov_matrix, weights)
            
            # Risk contribution of each asset
            contrib = weights * marginal_contrib / portfolio_std
            
            # Target equal contribution
            target_contrib = portfolio_std / len(weights)
            
            # Minimize squared deviations from target
            return np.sum((contrib - target_contrib) ** 2)
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
            {'type': 'ineq', 'fun': lambda x: x}  # All weights >= 0
        ]
        
        # Optimize
        result = minimize(risk_contribution_objective, init_weights, 
                         method='SLSQP', constraints=constraints)
        
        # Calculate final metrics
        opt_return, opt_risk = self.calculate_portfolio_metrics(result.x, returns)
        
        return {
            'weights': result.x,
            'expected_return': opt_return,
            'risk': opt_risk,
            'sharpe_ratio': (opt_return - 0.02) / opt_risk if opt_risk > 0 else 0,
            'success': result.success
        }
    
    def calculate_var(self, confidence_level: float = None) -> Dict[str, float]:
        """
        Calculate Value at Risk (VaR) for portfolio
        
        Args:
            confidence_level: Confidence level (default 0.95)
            
        Returns:
            VaR metrics
        """
        if confidence_level is None:
            confidence_level = self.confidence_level
        
        if self.optimal_weights is None or not self.assets:
            return {'var_1d': 0, 'var_1w': 0, 'var_1m': 0, 'parametric_var_1d': 0, 'confidence_level': confidence_level}
        
        # Get portfolio returns
        returns_data = []
        for i, symbol in enumerate(self.assets):
            if symbol in self.historical_data:
                prices = self.historical_data[symbol]['close']
                returns = self.calculate_returns(prices)
                if len(returns) > 0:
                    weighted_returns = returns * self.optimal_weights[i]
                    returns_data.append(weighted_returns)
        
        if not returns_data:
            return {'var_1d': 0, 'var_1w': 0, 'var_1m': 0, 'parametric_var_1d': 0, 'confidence_level': confidence_level}
        
        # Portfolio returns
        portfolio_returns = pd.concat(returns_data, axis=1).sum(axis=1)
        
        # Calculate VaR using historical method
        var_1d = np.percentile(portfolio_returns, (1 - confidence_level) * 100)
        var_1w = var_1d * np.sqrt(5)  # Weekly VaR
        var_1m = var_1d * np.sqrt(21)  # Monthly VaR
        
        # Calculate parametric VaR
        mean_return = portfolio_returns.mean()
        std_return = portfolio_returns.std()
        z_score = norm.ppf(1 - confidence_level)
        
        parametric_var_1d = mean_return + z_score * std_return
        
        return {
            'var_1d': abs(var_1d),
            'var_1w': abs(var_1w),
            'var_1m': abs(var_1m),
            'parametric_var_1d': abs(parametric_var_1d),
            'confidence_level': confidence_level
        }
    
    def check_rebalance_needed(self, current_positions: Dict[str, float]) -> Dict[str, Any]:
        """
        Check if portfolio rebalancing is needed
        
        Args:
            current_positions: Current position values by symbol
            
        Returns:
            Rebalancing requirements
        """
        if not self.optimal_weights or not self.assets:
            return {'needed': False, 'reason': 'No optimal weights calculated'}
        
        # Calculate total portfolio value
        total_value = sum(current_positions.values())
        
        if total_value == 0:
            return {'needed': True, 'reason': 'No positions'}
        
        # Calculate current weights
        current_weights = {}
        deviations = {}
        
        for i, symbol in enumerate(self.assets):
            current_value = current_positions.get(symbol, 0)
            current_weight = current_value / total_value if total_value > 0 else 0
            optimal_weight = self.optimal_weights[i]
            
            current_weights[symbol] = current_weight
            deviation = abs(current_weight - optimal_weight)
            deviations[symbol] = deviation
        
        # Check if any deviation exceeds threshold
        max_deviation = max(deviations.values())
        needs_rebalance = max_deviation > self.rebalance_threshold
        
        # Calculate trades needed
        trades = {}
        for i, symbol in enumerate(self.assets):
            current_value = current_positions.get(symbol, 0)
            target_value = self.optimal_weights[i] * total_value
            trade_value = target_value - current_value
            
            if abs(trade_value) > total_value * 0.01:  # 1% minimum trade
                trades[symbol] = {
                    'current_value': current_value,
                    'target_value': target_value,
                    'trade_value': trade_value,
                    'action': 'BUY' if trade_value > 0 else 'SELL'
                }
        
        return {
            'needed': needs_rebalance,
            'max_deviation': max_deviation,
            'current_weights': current_weights,
            'optimal_weights': {s: w for s, w in zip(self.assets, self.optimal_weights)},
            'trades_required': trades,
            'reason': f"Max deviation: {max_deviation:.2%}"
        }
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary"""
        summary = {
            'assets': self.assets,
            'num_assets': len(self.assets),
            'optimal_weights': None,
            'correlation_matrix': None,
            'var_metrics': None,
            'expected_metrics': None
        }
        
        # Add optimal weights
        if self.optimal_weights is not None:
            summary['optimal_weights'] = {
                symbol: float(weight) 
                for symbol, weight in zip(self.assets, self.optimal_weights)
            }
        
        # Add correlation matrix
        if self.correlation_matrix is not None:
            summary['correlation_matrix'] = self.correlation_matrix.to_dict()
        
        # Calculate VaR
        summary['var_metrics'] = self.calculate_var()
        
        # Expected metrics if optimized
        if self.optimal_weights is not None and len(self.assets) > 0:
            returns_data = {}
            for symbol in self.assets:
                if symbol in self.historical_data:
                    prices = self.historical_data[symbol]['close']
                    returns = self.calculate_returns(prices)
                    returns_data[symbol] = returns
            
            if returns_data:
                returns_df = pd.DataFrame(returns_data).dropna()
                exp_return, exp_risk = self.calculate_portfolio_metrics(
                    self.optimal_weights, returns_df
                )
                
                summary['expected_metrics'] = {
                    'annual_return': exp_return,
                    'annual_volatility': exp_risk,
                    'sharpe_ratio': (exp_return - 0.02) / exp_risk if exp_risk > 0 else 0
                }
        
        return summary
    
    def analyze_asset_contribution(self) -> Dict[str, Dict[str, float]]:
        """Analyze each asset's contribution to portfolio risk and return"""
        if not self.optimal_weights or not self.assets:
            return {}
        
        contributions = {}
        
        # Prepare returns data
        returns_data = {}
        for symbol in self.assets:
            if symbol in self.historical_data:
                prices = self.historical_data[symbol]['close']
                returns = self.calculate_returns(prices)
                returns_data[symbol] = returns
        
        if not returns_data:
            return {}
        
        returns_df = pd.DataFrame(returns_data).dropna()
        cov_matrix = returns_df.cov() * 252
        mean_returns = returns_df.mean() * 252
        
        # Portfolio metrics
        portfolio_return = np.sum(self.optimal_weights * mean_returns)
        portfolio_var = np.dot(self.optimal_weights.T, 
                              np.dot(cov_matrix, self.optimal_weights))
        portfolio_std = np.sqrt(portfolio_var)
        
        # Calculate contributions
        marginal_contrib = np.dot(cov_matrix, self.optimal_weights)
        
        for i, symbol in enumerate(self.assets):
            weight = self.optimal_weights[i]
            
            # Return contribution
            return_contrib = weight * mean_returns.iloc[i] / portfolio_return \
                           if portfolio_return != 0 else 0
            
            # Risk contribution
            risk_contrib = weight * marginal_contrib[i] / portfolio_var \
                         if portfolio_var != 0 else 0
            
            contributions[symbol] = {
                'weight': float(weight),
                'return_contribution': float(return_contrib),
                'risk_contribution': float(risk_contrib),
                'expected_return': float(mean_returns.iloc[i]),
                'standalone_risk': float(np.sqrt(cov_matrix.iloc[i, i]))
            }
        
        return contributions