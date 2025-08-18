"""
Grid Trading Optimizer
Optimizes grid parameters based on market conditions and historical data
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from scipy import optimize
from sklearn.cluster import KMeans

logger = logging.getLogger(__name__)

@dataclass
class OptimizationResult:
    """Grid optimization result"""
    upper_price: float
    lower_price: float
    grid_levels: int
    optimal_spacing: str  # fixed, dynamic, geometric
    expected_return: float
    risk_score: float
    confidence: float
    recommendations: List[str]

class GridOptimizer:
    """Optimizes grid trading parameters for maximum profitability"""
    
    def __init__(self, market_data_provider):
        """
        Initialize Grid Optimizer
        
        Args:
            market_data_provider: Provider for historical market data
        """
        self.data_provider = market_data_provider
        self.optimization_cache = {}
        
    async def optimize_grid_parameters(
        self,
        symbol: str,
        investment: float,
        timeframe: str = "1h",
        lookback_days: int = 30
    ) -> OptimizationResult:
        """
        Optimize grid parameters based on historical data
        
        Args:
            symbol: Trading symbol
            investment: Total investment amount
            timeframe: Candle timeframe for analysis
            lookback_days: Days of historical data to analyze
            
        Returns:
            Optimized grid parameters
        """
        try:
            # Get historical data
            historical_data = await self._get_historical_data(
                symbol, timeframe, lookback_days
            )
            
            if historical_data.empty:
                raise ValueError("No historical data available")
            
            # Analyze market structure
            market_analysis = self._analyze_market_structure(historical_data)
            
            # Find optimal price range
            upper_price, lower_price = self._find_optimal_range(
                historical_data, market_analysis
            )
            
            # Calculate optimal grid levels
            grid_levels = self._calculate_optimal_levels(
                upper_price, lower_price, investment, historical_data
            )
            
            # Determine best spacing type
            spacing_type = self._determine_spacing_type(market_analysis)
            
            # Calculate expected returns
            expected_return = self._calculate_expected_return(
                historical_data, upper_price, lower_price, grid_levels
            )
            
            # Assess risk
            risk_score = self._calculate_risk_score(
                historical_data, market_analysis
            )
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                market_analysis, risk_score
            )
            
            result = OptimizationResult(
                upper_price=upper_price,
                lower_price=lower_price,
                grid_levels=grid_levels,
                optimal_spacing=spacing_type,
                expected_return=expected_return,
                risk_score=risk_score,
                confidence=market_analysis["confidence"],
                recommendations=recommendations
            )
            
            # Cache result
            cache_key = f"{symbol}_{timeframe}_{lookback_days}"
            self.optimization_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Error optimizing grid parameters: {e}")
            raise
    
    def _analyze_market_structure(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze market structure and characteristics"""
        analysis = {}
        
        # Calculate returns
        data['returns'] = data['close'].pct_change()
        
        # Trend analysis
        sma_20 = data['close'].rolling(20).mean()
        sma_50 = data['close'].rolling(50).mean()
        
        if len(data) >= 50:
            current_price = data['close'].iloc[-1]
            analysis['trend'] = 'bullish' if current_price > sma_50.iloc[-1] else 'bearish'
            analysis['trend_strength'] = abs(current_price - sma_50.iloc[-1]) / sma_50.iloc[-1]
        else:
            analysis['trend'] = 'neutral'
            analysis['trend_strength'] = 0
        
        # Volatility analysis
        analysis['volatility'] = data['returns'].std() * np.sqrt(24)  # Daily volatility
        analysis['atr'] = self._calculate_atr(data)
        
        # Range analysis
        analysis['range_bound'] = self._detect_range_bound(data)
        analysis['support_levels'] = self._find_support_resistance(data, 'support')
        analysis['resistance_levels'] = self._find_support_resistance(data, 'resistance')
        
        # Market regime
        analysis['regime'] = self._detect_market_regime(data)
        
        # Confidence score
        analysis['confidence'] = self._calculate_confidence(analysis)
        
        return analysis
    
    def _find_optimal_range(
        self,
        data: pd.DataFrame,
        analysis: Dict[str, Any]
    ) -> Tuple[float, float]:
        """Find optimal price range for grid"""
        
        current_price = data['close'].iloc[-1]
        
        if analysis['range_bound']:
            # Use detected range
            upper = max(analysis['resistance_levels'][:2]) if analysis['resistance_levels'] else current_price * 1.05
            lower = min(analysis['support_levels'][:2]) if analysis['support_levels'] else current_price * 0.95
        else:
            # Use volatility-based range
            atr = analysis['atr']
            volatility_multiplier = 2.5 if analysis['volatility'] > 0.03 else 2.0
            
            upper = current_price + (atr * volatility_multiplier)
            lower = current_price - (atr * volatility_multiplier)
        
        # Adjust for trend
        if analysis['trend'] == 'bullish':
            # Shift range up
            shift = (upper - lower) * 0.1
            upper += shift
            lower += shift
        elif analysis['trend'] == 'bearish':
            # Shift range down
            shift = (upper - lower) * 0.1
            upper -= shift
            lower -= shift
        
        return round(upper, 2), round(lower, 2)
    
    def _calculate_optimal_levels(
        self,
        upper_price: float,
        lower_price: float,
        investment: float,
        data: pd.DataFrame
    ) -> int:
        """Calculate optimal number of grid levels"""
        
        price_range = upper_price - lower_price
        avg_price = (upper_price + lower_price) / 2
        
        # Base calculation on investment size and price
        base_levels = int(investment / (avg_price * 10))  # $10 per level minimum
        
        # Adjust for volatility
        volatility = data['close'].pct_change().std()
        if volatility > 0.03:
            # High volatility - fewer levels
            levels = max(5, base_levels // 2)
        elif volatility < 0.01:
            # Low volatility - more levels
            levels = min(50, base_levels * 2)
        else:
            levels = base_levels
        
        # Ensure reasonable range
        levels = max(5, min(50, levels))
        
        return levels
    
    def _determine_spacing_type(self, analysis: Dict[str, Any]) -> str:
        """Determine optimal grid spacing type"""
        
        if analysis['regime'] == 'trending':
            if analysis['volatility'] > 0.03:
                return 'geometric'  # Better for trending volatile markets
            else:
                return 'dynamic'  # Adjust with trend
        elif analysis['regime'] == 'ranging':
            return 'fixed'  # Best for range-bound markets
        else:  # choppy
            return 'fibonacci'  # Natural support/resistance levels
    
    def _calculate_expected_return(
        self,
        data: pd.DataFrame,
        upper_price: float,
        lower_price: float,
        grid_levels: int
    ) -> float:
        """Calculate expected return based on historical performance"""
        
        # Simulate grid performance on historical data
        grid_spacing = (upper_price - lower_price) / (grid_levels - 1)
        
        # Count how many times price crossed grid levels
        crossings = 0
        for i in range(1, len(data)):
            prev_price = data['close'].iloc[i-1]
            curr_price = data['close'].iloc[i]
            
            # Count grid level crossings
            for level in range(grid_levels):
                grid_price = lower_price + (level * grid_spacing)
                if (prev_price <= grid_price <= curr_price) or (curr_price <= grid_price <= prev_price):
                    crossings += 1
        
        # Estimate profit per crossing (simplified)
        profit_per_crossing = grid_spacing * 0.001  # 0.1% profit per grid
        total_profit = crossings * profit_per_crossing
        
        # Annualize return
        days = len(data) / 24  # Assuming hourly data
        annual_return = (total_profit / ((upper_price + lower_price) / 2)) * (365 / days) * 100
        
        return round(annual_return, 2)
    
    def _calculate_risk_score(
        self,
        data: pd.DataFrame,
        analysis: Dict[str, Any]
    ) -> float:
        """Calculate risk score (0-100, lower is better)"""
        
        risk_score = 0
        
        # Volatility risk
        if analysis['volatility'] > 0.05:
            risk_score += 30
        elif analysis['volatility'] > 0.03:
            risk_score += 20
        else:
            risk_score += 10
        
        # Trend risk
        if analysis['trend_strength'] > 0.1:
            risk_score += 20  # Strong trend = higher risk for grid
        
        # Regime risk
        if analysis['regime'] == 'trending':
            risk_score += 15
        elif analysis['regime'] == 'choppy':
            risk_score += 10
        
        # Drawdown risk
        max_drawdown = self._calculate_max_drawdown(data)
        if max_drawdown > 0.2:
            risk_score += 25
        elif max_drawdown > 0.1:
            risk_score += 15
        else:
            risk_score += 5
        
        return min(100, risk_score)
    
    def _generate_recommendations(
        self,
        analysis: Dict[str, Any],
        risk_score: float
    ) -> List[str]:
        """Generate trading recommendations"""
        
        recommendations = []
        
        # Risk-based recommendations
        if risk_score > 70:
            recommendations.append("⚠️ High risk detected - consider reducing position size")
        elif risk_score < 30:
            recommendations.append("✅ Low risk environment - favorable for grid trading")
        
        # Trend recommendations
        if analysis['trend'] == 'bullish':
            recommendations.append("📈 Bullish trend - consider long-biased grid")
        elif analysis['trend'] == 'bearish':
            recommendations.append("📉 Bearish trend - consider short-biased grid")
        
        # Volatility recommendations
        if analysis['volatility'] > 0.04:
            recommendations.append("🌊 High volatility - use wider grid spacing")
        elif analysis['volatility'] < 0.01:
            recommendations.append("😴 Low volatility - use tighter grid spacing")
        
        # Regime recommendations
        if analysis['regime'] == 'ranging':
            recommendations.append("📊 Range-bound market - ideal for neutral grid")
        elif analysis['regime'] == 'trending':
            recommendations.append("🎯 Trending market - consider using trailing grid")
        
        # Support/Resistance recommendations
        if analysis['support_levels']:
            recommendations.append(f"🛡️ Strong support at {analysis['support_levels'][0]:.2f}")
        if analysis['resistance_levels']:
            recommendations.append(f"🚧 Strong resistance at {analysis['resistance_levels'][0]:.2f}")
        
        return recommendations
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        high = data['high']
        low = data['low']
        close = data['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        
        return atr
    
    def _detect_range_bound(self, data: pd.DataFrame) -> bool:
        """Detect if market is range-bound"""
        
        # Calculate price range
        price_range = data['high'].max() - data['low'].min()
        avg_price = data['close'].mean()
        range_pct = price_range / avg_price
        
        # Check if price stayed within a range
        if range_pct < 0.1:  # Less than 10% range
            # Check for mean reversion
            returns = data['close'].pct_change()
            autocorr = returns.autocorr(lag=1)
            
            if autocorr < -0.1:  # Negative autocorrelation = mean reverting
                return True
        
        return False
    
    def _find_support_resistance(
        self,
        data: pd.DataFrame,
        type: str = 'support'
    ) -> List[float]:
        """Find support and resistance levels using clustering"""
        
        if type == 'support':
            prices = data['low'].values
        else:
            prices = data['high'].values
        
        # Reshape for clustering
        prices_reshaped = prices.reshape(-1, 1)
        
        # Use KMeans to find clusters
        n_clusters = min(5, len(prices) // 10)
        if n_clusters < 2:
            return []
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        kmeans.fit(prices_reshaped)
        
        # Get cluster centers
        levels = sorted(kmeans.cluster_centers_.flatten())
        
        return levels
    
    def _detect_market_regime(self, data: pd.DataFrame) -> str:
        """Detect current market regime"""
        
        returns = data['close'].pct_change().dropna()
        
        # Calculate metrics
        trend = (data['close'].iloc[-1] - data['close'].iloc[0]) / data['close'].iloc[0]
        volatility = returns.std()
        skewness = returns.skew()
        
        # Classify regime
        if abs(trend) > 0.1:
            return 'trending'
        elif volatility < 0.01:
            return 'ranging'
        else:
            return 'choppy'
    
    def _calculate_confidence(self, analysis: Dict[str, Any]) -> float:
        """Calculate confidence score for optimization"""
        
        confidence = 50  # Base confidence
        
        # Adjust based on market conditions
        if analysis['regime'] == 'ranging':
            confidence += 20
        elif analysis['regime'] == 'trending':
            confidence -= 10
        
        if analysis['volatility'] < 0.02:
            confidence += 15
        elif analysis['volatility'] > 0.04:
            confidence -= 15
        
        if analysis['range_bound']:
            confidence += 10
        
        # Ensure within bounds
        confidence = max(0, min(100, confidence))
        
        return confidence
    
    def _calculate_max_drawdown(self, data: pd.DataFrame) -> float:
        """Calculate maximum drawdown"""
        
        cumulative = (1 + data['close'].pct_change()).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        
        return abs(drawdown.min())
    
    async def _get_historical_data(
        self,
        symbol: str,
        timeframe: str,
        lookback_days: int
    ) -> pd.DataFrame:
        """Get historical market data"""
        
        # This would interface with the actual data provider
        # For now, return empty DataFrame as placeholder
        return pd.DataFrame()
    
    def backtest_grid_strategy(
        self,
        data: pd.DataFrame,
        upper_price: float,
        lower_price: float,
        grid_levels: int,
        investment: float
    ) -> Dict[str, Any]:
        """Backtest grid strategy on historical data"""
        
        results = {
            "total_trades": 0,
            "winning_trades": 0,
            "total_profit": 0,
            "max_drawdown": 0,
            "sharpe_ratio": 0,
            "win_rate": 0
        }
        
        # Simulate grid trading
        grid_spacing = (upper_price - lower_price) / (grid_levels - 1)
        position_size = investment / grid_levels
        
        trades = []
        current_position = 0
        
        for i in range(1, len(data)):
            price = data['close'].iloc[i]
            
            # Check if price hits any grid level
            for level in range(grid_levels):
                grid_price = lower_price + (level * grid_spacing)
                
                # Simple simulation: buy below mid, sell above mid
                mid_price = (upper_price + lower_price) / 2
                
                if abs(price - grid_price) < grid_spacing * 0.1:  # Within 10% of grid level
                    if grid_price < mid_price and current_position < investment:
                        # Buy signal
                        trades.append({
                            'type': 'buy',
                            'price': grid_price,
                            'size': position_size
                        })
                        current_position += position_size
                        results["total_trades"] += 1
                        
                    elif grid_price > mid_price and current_position > 0:
                        # Sell signal
                        profit = (grid_price - mid_price) * position_size / mid_price
                        trades.append({
                            'type': 'sell',
                            'price': grid_price,
                            'size': position_size,
                            'profit': profit
                        })
                        current_position -= position_size
                        results["total_trades"] += 1
                        results["total_profit"] += profit
                        
                        if profit > 0:
                            results["winning_trades"] += 1
        
        # Calculate statistics
        if results["total_trades"] > 0:
            results["win_rate"] = (results["winning_trades"] / results["total_trades"]) * 100
        
        # Calculate Sharpe ratio (simplified)
        if trades:
            returns = [t.get('profit', 0) for t in trades if 'profit' in t]
            if returns:
                avg_return = np.mean(returns)
                std_return = np.std(returns)
                if std_return > 0:
                    results["sharpe_ratio"] = avg_return / std_return * np.sqrt(252)
        
        return results