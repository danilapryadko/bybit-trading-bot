"""
Moving Average Crossover Strategy
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from .base import BaseStrategy

logger = logging.getLogger(__name__)

class MovingAverageStrategy(BaseStrategy):
    """Strategy based on Moving Average crossovers"""
    
    def __init__(self, symbol: str, params: Dict[str, Any] = None):
        super().__init__(symbol, params)
        
        # MA specific parameters
        self.fast_period = self.params.get('fast_period', 9)
        self.slow_period = self.params.get('slow_period', 21)
        self.ma_type = self.params.get('ma_type', 'EMA')  # EMA or SMA
        self.signal_period = self.params.get('signal_period', 5)  # For MACD-like signal
        self.use_volume = self.params.get('use_volume', True)
        
    def calculate_sma(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average"""
        return prices.rolling(window=period).mean()
    
    def calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return prices.ewm(span=period, adjust=False).mean()
    
    def calculate_ma(self, prices: pd.Series, period: int, ma_type: str = 'EMA') -> pd.Series:
        """Calculate Moving Average based on type"""
        if ma_type.upper() == 'EMA':
            return self.calculate_ema(prices, period)
        else:
            return self.calculate_sma(prices, period)
    
    def analyze(self, market_data: Dict[str, Any]) -> Tuple[str, float, Dict[str, Any]]:
        """
        Analyze market using Moving Average crossover
        
        Returns:
            Tuple of (signal, confidence, metadata)
        """
        try:
            # Extract price data
            if 'klines' not in market_data or not market_data['klines']:
                return 'HOLD', 0.0, {'error': 'No kline data available'}
            
            klines = market_data['klines']
            
            # Convert to DataFrame
            df = pd.DataFrame(klines)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float) if 'volume' in df else 0
            
            # Calculate Moving Averages
            df['ma_fast'] = self.calculate_ma(df['close'], self.fast_period, self.ma_type)
            df['ma_slow'] = self.calculate_ma(df['close'], self.slow_period, self.ma_type)
            
            # Calculate crossover signals
            df['ma_diff'] = df['ma_fast'] - df['ma_slow']
            df['ma_diff_pct'] = (df['ma_diff'] / df['ma_slow']) * 100
            
            # Current values
            current_fast = df['ma_fast'].iloc[-1]
            current_slow = df['ma_slow'].iloc[-1]
            prev_fast = df['ma_fast'].iloc[-2] if len(df) > 1 else current_fast
            prev_slow = df['ma_slow'].iloc[-2] if len(df) > 1 else current_slow
            
            # Detect crossover
            signal = 'HOLD'
            confidence = 0.0
            crossover_type = None
            
            # Golden Cross (Bullish)
            if prev_fast <= prev_slow and current_fast > current_slow:
                signal = 'BUY'
                crossover_type = 'golden_cross'
                # Confidence based on crossover strength
                confidence = min(abs(df['ma_diff_pct'].iloc[-1]) / 2, 1.0)
                
            # Death Cross (Bearish)
            elif prev_fast >= prev_slow and current_fast < current_slow:
                signal = 'SELL'
                crossover_type = 'death_cross'
                # Confidence based on crossover strength
                confidence = min(abs(df['ma_diff_pct'].iloc[-1]) / 2, 1.0)
                
            # Trend following (no crossover but strong trend)
            elif abs(df['ma_diff_pct'].iloc[-1]) > 2:
                if current_fast > current_slow:
                    signal = 'BUY'
                    confidence = min(df['ma_diff_pct'].iloc[-1] / 5, 0.7)
                else:
                    signal = 'SELL'
                    confidence = min(abs(df['ma_diff_pct'].iloc[-1]) / 5, 0.7)
            
            # Volume confirmation
            if self.use_volume and 'volume' in df:
                volume_ma = df['volume'].rolling(window=20).mean()
                current_volume = df['volume'].iloc[-1]
                volume_ratio = current_volume / volume_ma.iloc[-1] if volume_ma.iloc[-1] > 0 else 1
                
                # Increase confidence if volume confirms signal
                if volume_ratio > 1.5 and signal != 'HOLD':
                    confidence = min(confidence * 1.2, 1.0)
            
            # Calculate trend strength
            trend_strength = self.calculate_trend_strength(df)
            
            # Adjust confidence based on trend strength
            confidence = confidence * (0.7 + 0.3 * trend_strength)
            
            # Prepare metadata
            metadata = {
                'ma_fast': round(current_fast, 2),
                'ma_slow': round(current_slow, 2),
                'ma_diff': round(current_fast - current_slow, 2),
                'ma_diff_pct': round(df['ma_diff_pct'].iloc[-1], 2),
                'crossover': crossover_type,
                'trend_strength': round(trend_strength, 2),
                'fast_period': self.fast_period,
                'slow_period': self.slow_period,
                'ma_type': self.ma_type
            }
            
            # Store last signal
            self.last_signal = signal
            self.last_signal_time = pd.Timestamp.now()
            
            return signal, confidence, metadata
            
        except Exception as e:
            logger.error(f"Error analyzing MA: {e}")
            return 'HOLD', 0.0, {'error': str(e)}
    
    def calculate_trend_strength(self, df: pd.DataFrame) -> float:
        """Calculate trend strength based on MA alignment"""
        try:
            # Check if MAs are properly aligned
            ma_fast = df['ma_fast'].tail(5)
            ma_slow = df['ma_slow'].tail(5)
            
            # Calculate how consistently fast MA is above/below slow MA
            alignment = (ma_fast > ma_slow).sum() / len(ma_fast)
            
            # Strong trend if consistently above (near 1) or below (near 0)
            strength = abs(alignment - 0.5) * 2
            
            # Also consider the angle of MAs
            fast_angle = (ma_fast.iloc[-1] - ma_fast.iloc[0]) / ma_fast.iloc[0]
            slow_angle = (ma_slow.iloc[-1] - ma_slow.iloc[0]) / ma_slow.iloc[0]
            
            # If both MAs moving in same direction, stronger trend
            if fast_angle * slow_angle > 0:
                strength = min(strength * 1.2, 1.0)
            
            return strength
            
        except:
            return 0.5
    
    def should_enter_position(self, signal: str, confidence: float, current_position: Optional[Dict]) -> bool:
        """Determine if should enter position based on MA strategy rules"""
        # Don't enter if already have position
        if current_position:
            return False
        
        # Check confidence threshold
        if confidence < self.min_confidence:
            return False
        
        # Only enter on BUY or SELL signals
        if signal == 'HOLD':
            return False
        
        return True
    
    def should_exit_position(self, current_position: Dict, market_data: Dict[str, Any]) -> bool:
        """Determine if should exit position based on MA strategy rules"""
        if not current_position:
            return False
        
        # Analyze current market
        signal, confidence, metadata = self.analyze(market_data)
        
        position_side = current_position.get('side')
        
        # Exit on opposite crossover
        if position_side == 'Buy' and metadata.get('crossover') == 'death_cross':
            return True
        elif position_side == 'Sell' and metadata.get('crossover') == 'golden_cross':
            return True
        
        # Exit on strong opposite signal
        if position_side == 'Buy' and signal == 'SELL' and confidence > 0.7:
            return True
        elif position_side == 'Sell' and signal == 'BUY' and confidence > 0.7:
            return True
        
        # Exit if trend weakens significantly
        if metadata.get('trend_strength', 0) < 0.3:
            return True
        
        # Check stop loss and take profit
        pnl_percent = current_position.get('unrealizedPnl', 0) / current_position.get('size', 1) * 100
        if pnl_percent >= self.take_profit_percent or pnl_percent <= -self.stop_loss_percent:
            return True
        
        return False
    
    def get_config(self) -> Dict[str, Any]:
        """Get strategy configuration"""
        config = super().to_dict()
        config.update({
            'fast_period': self.fast_period,
            'slow_period': self.slow_period,
            'ma_type': self.ma_type,
            'signal_period': self.signal_period,
            'use_volume': self.use_volume
        })
        return config