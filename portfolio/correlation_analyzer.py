"""
Correlation Analysis Module
Analyzes correlations between assets for diversification
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from scipy import stats
from sklearn.decomposition import PCA
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class CorrelationAnalyzer:
    """Advanced correlation and dependency analysis"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.correlations = {}
        self.rolling_correlations = {}
        self.correlation_stability = {}
        
        # Analysis parameters
        self.min_correlation = self.config.get('min_correlation', 0.3)
        self.high_correlation = self.config.get('high_correlation', 0.7)
        self.rolling_window = self.config.get('rolling_window', 30)  # days
        self.stability_threshold = self.config.get('stability_threshold', 0.2)
        
    def analyze_correlation(self, data1: pd.Series, data2: pd.Series, 
                           method: str = 'pearson') -> Dict[str, float]:
        """
        Analyze correlation between two time series
        
        Args:
            data1: First time series
            data2: Second time series
            method: Correlation method ('pearson', 'spearman', 'kendall')
            
        Returns:
            Correlation metrics
        """
        # Align data
        aligned_data = pd.DataFrame({'data1': data1, 'data2': data2}).dropna()
        
        if len(aligned_data) < 10:
            return {'correlation': 0, 'p_value': 1, 'significant': False}
        
        # Calculate correlation
        if method == 'pearson':
            corr, p_value = stats.pearsonr(aligned_data['data1'], aligned_data['data2'])
        elif method == 'spearman':
            corr, p_value = stats.spearmanr(aligned_data['data1'], aligned_data['data2'])
        elif method == 'kendall':
            corr, p_value = stats.kendalltau(aligned_data['data1'], aligned_data['data2'])
        else:
            raise ValueError(f"Unknown correlation method: {method}")
        
        return {
            'correlation': corr,
            'p_value': p_value,
            'significant': p_value < 0.05,
            'method': method,
            'n_observations': len(aligned_data)
        }
    
    def calculate_rolling_correlation(self, data1: pd.Series, data2: pd.Series,
                                     window: int = None) -> pd.Series:
        """
        Calculate rolling correlation
        
        Args:
            data1: First time series
            data2: Second time series
            window: Rolling window size
            
        Returns:
            Rolling correlation series
        """
        if window is None:
            window = self.rolling_window
        
        # Align data
        aligned_data = pd.DataFrame({'data1': data1, 'data2': data2}).dropna()
        
        # Calculate rolling correlation
        rolling_corr = aligned_data['data1'].rolling(window).corr(aligned_data['data2'])
        
        return rolling_corr
    
    def analyze_correlation_stability(self, data1: pd.Series, data2: pd.Series) -> Dict[str, Any]:
        """
        Analyze stability of correlation over time
        
        Args:
            data1: First time series
            data2: Second time series
            
        Returns:
            Stability metrics
        """
        # Calculate rolling correlation
        rolling_corr = self.calculate_rolling_correlation(data1, data2)
        rolling_corr = rolling_corr.dropna()
        
        if len(rolling_corr) < 2:
            return {
                'stable': False,
                'mean_correlation': 0,
                'std_correlation': 0,
                'coefficient_of_variation': 0
            }
        
        # Calculate stability metrics
        mean_corr = rolling_corr.mean()
        std_corr = rolling_corr.std()
        cv = std_corr / abs(mean_corr) if mean_corr != 0 else float('inf')
        
        # Determine if correlation is stable
        is_stable = cv < self.stability_threshold
        
        # Calculate correlation regime changes
        regime_changes = self._detect_regime_changes(rolling_corr)
        
        return {
            'stable': is_stable,
            'mean_correlation': float(mean_corr),
            'std_correlation': float(std_corr),
            'coefficient_of_variation': float(cv),
            'min_correlation': float(rolling_corr.min()),
            'max_correlation': float(rolling_corr.max()),
            'current_correlation': float(rolling_corr.iloc[-1]) if len(rolling_corr) > 0 else 0,
            'regime_changes': regime_changes
        }
    
    def _detect_regime_changes(self, rolling_corr: pd.Series) -> List[Dict[str, Any]]:
        """Detect significant changes in correlation regime"""
        regime_changes = []
        
        if len(rolling_corr) < 10:
            return regime_changes
        
        # Use rolling mean and std to detect changes
        rolling_mean = rolling_corr.rolling(10).mean()
        rolling_std = rolling_corr.rolling(10).std()
        
        # Detect when correlation moves beyond 2 standard deviations
        upper_bound = rolling_mean + 2 * rolling_std
        lower_bound = rolling_mean - 2 * rolling_std
        
        # Find regime changes
        for i in range(1, len(rolling_corr)):
            if pd.notna(upper_bound.iloc[i]) and pd.notna(lower_bound.iloc[i]):
                if rolling_corr.iloc[i] > upper_bound.iloc[i] or \
                   rolling_corr.iloc[i] < lower_bound.iloc[i]:
                    regime_changes.append({
                        'index': i,
                        'date': rolling_corr.index[i] if hasattr(rolling_corr.index, 'date') else i,
                        'correlation': float(rolling_corr.iloc[i]),
                        'expected_range': (float(lower_bound.iloc[i]), float(upper_bound.iloc[i]))
                    })
        
        return regime_changes
    
    def analyze_portfolio_correlations(self, returns_data: Dict[str, pd.Series]) -> Dict[str, Any]:
        """
        Analyze correlations across entire portfolio
        
        Args:
            returns_data: Dictionary of returns by symbol
            
        Returns:
            Portfolio correlation analysis
        """
        if len(returns_data) < 2:
            return {'error': 'Need at least 2 assets for correlation analysis'}
        
        # Create returns DataFrame
        returns_df = pd.DataFrame(returns_data).dropna()
        
        # Calculate correlation matrix
        corr_matrix = returns_df.corr()
        
        # Calculate average correlation
        n_assets = len(returns_data)
        upper_triangle = np.triu(corr_matrix.values, k=1)
        avg_correlation = upper_triangle.sum() / ((n_assets * (n_assets - 1)) / 2)
        
        # Find highly correlated pairs
        highly_correlated = []
        for i in range(n_assets):
            for j in range(i + 1, n_assets):
                corr_value = corr_matrix.iloc[i, j]
                if abs(corr_value) > self.high_correlation:
                    highly_correlated.append({
                        'asset1': corr_matrix.index[i],
                        'asset2': corr_matrix.columns[j],
                        'correlation': float(corr_value)
                    })
        
        # Calculate diversification ratio
        # Equal weight assumption for simplicity
        weights = np.ones(n_assets) / n_assets
        portfolio_std = np.sqrt(np.dot(weights.T, np.dot(returns_df.cov(), weights)))
        individual_stds = returns_df.std()
        weighted_avg_std = np.sum(weights * individual_stds)
        diversification_ratio = weighted_avg_std / portfolio_std if portfolio_std > 0 else 1
        
        # PCA analysis for dimensionality
        explained_variance = []
        effective_assets = n_assets
        
        if len(returns_df) > 0 and n_assets > 1:
            try:
                pca = PCA()
                pca.fit(returns_df)
                explained_variance = pca.explained_variance_ratio_
                
                # Calculate effective number of assets (using entropy)
                eigenvalues = pca.explained_variance_
                eigenvalues = eigenvalues / eigenvalues.sum()
                entropy = -np.sum(eigenvalues * np.log(eigenvalues + 1e-10))
                effective_assets = np.exp(entropy)
            except:
                pass
        
        
        return {
            'correlation_matrix': corr_matrix.to_dict(),
            'average_correlation': float(avg_correlation),
            'highly_correlated_pairs': highly_correlated,
            'diversification_ratio': float(diversification_ratio),
            'effective_assets': float(effective_assets),
            'pca_explained_variance': explained_variance.tolist()[:3],  # Top 3 components
            'correlation_range': {
                'min': float(upper_triangle[upper_triangle != 0].min()) if upper_triangle[upper_triangle != 0].size > 0 else 0,
                'max': float(upper_triangle.max())
            }
        }
    
    def calculate_beta(self, asset_returns: pd.Series, 
                      market_returns: pd.Series) -> Dict[str, float]:
        """
        Calculate beta relative to market
        
        Args:
            asset_returns: Asset return series
            market_returns: Market return series
            
        Returns:
            Beta metrics
        """
        # Align data
        aligned_data = pd.DataFrame({
            'asset': asset_returns,
            'market': market_returns
        }).dropna()
        
        if len(aligned_data) < 10:
            return {'beta': 1, 'alpha': 0, 'r_squared': 0}
        
        # Calculate beta using linear regression
        X = aligned_data['market'].values.reshape(-1, 1)
        y = aligned_data['asset'].values
        
        # Add constant for alpha
        X_with_const = np.column_stack([np.ones(len(X)), X])
        
        # OLS regression
        coeffs = np.linalg.lstsq(X_with_const, y, rcond=None)[0]
        alpha, beta = coeffs[0], coeffs[1]
        
        # Calculate R-squared
        y_pred = alpha + beta * aligned_data['market']
        ss_res = np.sum((aligned_data['asset'] - y_pred) ** 2)
        ss_tot = np.sum((aligned_data['asset'] - aligned_data['asset'].mean()) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        return {
            'beta': float(beta),
            'alpha': float(alpha),
            'r_squared': float(r_squared),
            'n_observations': len(aligned_data)
        }
    
    def find_hedge_opportunities(self, returns_data: Dict[str, pd.Series]) -> List[Dict[str, Any]]:
        """
        Find potential hedging opportunities based on negative correlations
        
        Args:
            returns_data: Dictionary of returns by symbol
            
        Returns:
            List of hedge opportunities
        """
        hedge_opportunities = []
        symbols = list(returns_data.keys())
        
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                symbol1, symbol2 = symbols[i], symbols[j]
                
                # Analyze correlation
                corr_analysis = self.analyze_correlation(
                    returns_data[symbol1], 
                    returns_data[symbol2]
                )
                
                # Check for negative correlation (good for hedging)
                if corr_analysis['correlation'] < -self.min_correlation:
                    # Analyze stability
                    stability = self.analyze_correlation_stability(
                        returns_data[symbol1],
                        returns_data[symbol2]
                    )
                    
                    hedge_opportunities.append({
                        'asset1': symbol1,
                        'asset2': symbol2,
                        'correlation': corr_analysis['correlation'],
                        'stable': stability['stable'],
                        'hedge_quality': abs(corr_analysis['correlation']),
                        'p_value': corr_analysis['p_value']
                    })
        
        # Sort by hedge quality
        hedge_opportunities.sort(key=lambda x: x['hedge_quality'], reverse=True)
        
        return hedge_opportunities
    
    def calculate_correlation_risk(self, correlations: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate risk metrics based on correlations
        
        Args:
            correlations: Correlation matrix
            
        Returns:
            Correlation risk metrics
        """
        n_assets = len(correlations)
        
        # Average correlation (excluding diagonal)
        upper_triangle = np.triu(correlations.values, k=1)
        avg_corr = upper_triangle.sum() / ((n_assets * (n_assets - 1)) / 2)
        
        # Maximum correlation
        max_corr = upper_triangle.max()
        
        # Correlation concentration (how many pairs are highly correlated)
        high_corr_count = np.sum(upper_triangle > self.high_correlation)
        total_pairs = (n_assets * (n_assets - 1)) / 2
        correlation_concentration = high_corr_count / total_pairs if total_pairs > 0 else 0
        
        # Systemic risk indicator (if all assets are positively correlated)
        positive_corr_ratio = np.sum(upper_triangle > 0) / np.sum(upper_triangle != 0) \
                            if np.sum(upper_triangle != 0) > 0 else 0
        
        return {
            'average_correlation': float(avg_corr),
            'max_correlation': float(max_corr),
            'correlation_concentration': float(correlation_concentration),
            'positive_correlation_ratio': float(positive_corr_ratio),
            'systemic_risk_score': float(avg_corr * positive_corr_ratio),
            'diversification_quality': float(1 - avg_corr) if avg_corr < 1 else 0
        }