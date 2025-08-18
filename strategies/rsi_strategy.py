"""
RSI (Relative Strength Index) Strategy
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from .base import BaseStrategy

logger = logging.getLogger(__name__)

class RSIStrategy(BaseStrategy):
    """Strategy based on RSI indicator"""
    
    def __init__(self, symbol: str, params: Dict[str, Any] = None):
        super().__init__(symbol, params)
        
        # RSI specific parameters
        self.rsi_period = self.params.get('rsi_period', 14)
        self.rsi_oversold = self.params.get('rsi_oversold', 30)
        self.rsi_overbought = self.params.get('rsi_overbought', 70)
        self.rsi_neutral_low = self.params.get('rsi_neutral_low', 45)
        self.rsi_neutral_high = self.params.get('rsi_neutral_high', 55)
        
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def analyze(self, market_data: Dict[str, Any]) -> Tuple[str, float, Dict[str, Any]]:
        """
        Analyze market using RSI indicator
        
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
            
            # Calculate RSI
            df['rsi'] = self.calculate_rsi(df['close'], self.rsi_period)
            
            # Get current RSI value
            current_rsi = df['rsi'].iloc[-1]
            prev_rsi = df['rsi'].iloc[-2] if len(df) > 1 else current_rsi
            
            # Generate signal
            signal = 'HOLD'
            confidence = 0.0
            
            if current_rsi < self.rsi_oversold:
                signal = 'BUY'
                # Stronger signal the lower RSI goes
                confidence = (self.rsi_oversold - current_rsi) / self.rsi_oversold
                confidence = min(confidence * 1.5, 1.0)  # Boost confidence for extreme oversold
                
            elif current_rsi > self.rsi_overbought:
                signal = 'SELL'
                # Stronger signal the higher RSI goes
                confidence = (current_rsi - self.rsi_overbought) / (100 - self.rsi_overbought)
                confidence = min(confidence * 1.5, 1.0)  # Boost confidence for extreme overbought
                
            # Check for RSI divergence
            divergence = self.check_divergence(df)
            if divergence:
                confidence = min(confidence + 0.2, 1.0)
            
            # Prepare metadata
            metadata = {
                'rsi': round(current_rsi, 2),
                'rsi_prev': round(prev_rsi, 2),
                'rsi_change': round(current_rsi - prev_rsi, 2),
                'oversold_threshold': self.rsi_oversold,
                'overbought_threshold': self.rsi_overbought,
                'divergence': divergence,
                'period': self.rsi_period
            }
            
            # Store last signal
            self.last_signal = signal
            self.last_signal_time = pd.Timestamp.now()
            
            return signal, confidence, metadata
            
        except Exception as e:
            logger.error(f"Error analyzing RSI: {e}")
            return 'HOLD', 0.0, {'error': str(e)}
    
    def check_divergence(self, df: pd.DataFrame) -> str:
        """Check for RSI divergence patterns"""
        if len(df) < 10:
            return None
        
        # Get recent peaks and troughs
        rsi = df['rsi'].tail(10)
        price = df['close'].tail(10)
        
        # Bullish divergence: price makes lower low, RSI makes higher low
        if price.iloc[-1] < price.iloc[-5] and rsi.iloc[-1] > rsi.iloc[-5]:
            if rsi.iloc[-1] < 40:  # Only in oversold territory
                return 'bullish'
        
        # Bearish divergence: price makes higher high, RSI makes lower high
        if price.iloc[-1] > price.iloc[-5] and rsi.iloc[-1] < rsi.iloc[-5]:
            if rsi.iloc[-1] > 60:  # Only in overbought territory
                return 'bearish'
        
        return None
    
    def should_enter_position(self, signal: str, confidence: float, current_position: Optional[Dict]) -> bool:
        """Determine if should enter position based on RSI strategy rules"""
        # Don't enter if already have position
        if current_position:
            return False
        
        # Check confidence threshold
        if confidence < self.min_confidence:
            return False
        
        # Only enter on BUY or SELL signals
        if signal == 'HOLD':
            return False
        
        # Additional filters can be added here
        # For example: volume confirmation, trend alignment, etc.
        
        return True
    
    def should_exit_position(self, current_position: Dict, market_data: Dict[str, Any]) -> bool:
        """Determine if should exit position based on RSI strategy rules"""
        if not current_position:
            return False
        
        # Analyze current market
        signal, confidence, metadata = self.analyze(market_data)
        current_rsi = metadata.get('rsi', 50)
        
        position_side = current_position.get('side')
        
        # Exit long position
        if position_side == 'Buy':
            # Exit if RSI is overbought
            if current_rsi > self.rsi_overbought:
                return True
            # Exit on strong sell signal
            if signal == 'SELL' and confidence > 0.7:
                return True
            # Exit if RSI crosses below neutral from above
            if current_rsi < self.rsi_neutral_high and metadata.get('rsi_prev', 50) > self.rsi_neutral_high:
                return True
        
        # Exit short position
        elif position_side == 'Sell':
            # Exit if RSI is oversold
            if current_rsi < self.rsi_oversold:
                return True
            # Exit on strong buy signal
            if signal == 'BUY' and confidence > 0.7:
                return True
            # Exit if RSI crosses above neutral from below
            if current_rsi > self.rsi_neutral_low and metadata.get('rsi_prev', 50) < self.rsi_neutral_low:
                return True
        
        # Check stop loss and take profit (handled by exchange usually)
        pnl_percent = current_position.get('unrealizedPnl', 0) / current_position.get('size', 1) * 100
        if pnl_percent >= self.take_profit_percent or pnl_percent <= -self.stop_loss_percent:
            return True
        
        return False
    
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Generate trading signals for backtesting"""
        import pandas as pd
        signals = pd.Series(0, index=data.index)
        
        # Calculate RSI
        rsi = self.calculate_rsi(data['close'], self.rsi_period)
        
        # Generate signals
        signals[rsi < self.rsi_oversold] = 1  # Buy signal
        signals[rsi > self.rsi_overbought] = -1  # Sell signal
        
        return signals
    
    def get_config(self) -> Dict[str, Any]:
        """Get strategy configuration"""
        config = super().to_dict()
        config.update({
            'rsi_period': self.rsi_period,
            'rsi_oversold': self.rsi_oversold,
            'rsi_overbought': self.rsi_overbought,
            'rsi_neutral_low': self.rsi_neutral_low,
            'rsi_neutral_high': self.rsi_neutral_high
        })
        return config