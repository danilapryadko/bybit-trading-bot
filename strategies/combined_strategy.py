"""
Combined Strategy using multiple indicators
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
from .base import BaseStrategy
from .rsi_strategy import RSIStrategy
from .ma_strategy import MovingAverageStrategy

logger = logging.getLogger(__name__)

class CombinedStrategy(BaseStrategy):
    """Strategy combining RSI, MA, and other indicators"""
    
    def __init__(self, symbol: str, params: Dict[str, Any] = None):
        super().__init__(symbol, params)
        
        # Initialize sub-strategies
        self.rsi_strategy = RSIStrategy(symbol, params)
        self.ma_strategy = MovingAverageStrategy(symbol, params)
        
        # Combined strategy parameters
        self.weight_rsi = self.params.get('weight_rsi', 0.4)
        self.weight_ma = self.params.get('weight_ma', 0.4)
        self.weight_volume = self.params.get('weight_volume', 0.2)
        self.require_confirmation = self.params.get('require_confirmation', True)
        self.min_indicators_agree = self.params.get('min_indicators_agree', 2)
        
        # Bollinger Bands parameters
        self.bb_period = self.params.get('bb_period', 20)
        self.bb_std = self.params.get('bb_std', 2)
        
    def calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower
    
    def calculate_volume_profile(self, df: pd.DataFrame) -> Dict[str, float]:
        """Analyze volume profile"""
        if 'volume' not in df:
            return {'volume_trend': 0, 'volume_strength': 0}
        
        volume = df['volume'].astype(float)
        volume_ma = volume.rolling(window=20).mean()
        
        # Current volume vs average
        current_volume = volume.iloc[-1]
        avg_volume = volume_ma.iloc[-1] if not pd.isna(volume_ma.iloc[-1]) else current_volume
        
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Volume trend (increasing/decreasing)
        volume_trend = 1 if volume.tail(5).mean() > volume.tail(20).mean() else -1
        
        return {
            'volume_ratio': volume_ratio,
            'volume_trend': volume_trend,
            'volume_strength': min(volume_ratio / 2, 1.0)
        }
    
    def analyze(self, market_data: Dict[str, Any]) -> Tuple[str, float, Dict[str, Any]]:
        """
        Analyze market using multiple indicators
        
        Returns:
            Tuple of (signal, confidence, metadata)
        """
        try:
            # Get signals from sub-strategies
            rsi_signal, rsi_confidence, rsi_meta = self.rsi_strategy.analyze(market_data)
            ma_signal, ma_confidence, ma_meta = self.ma_strategy.analyze(market_data)
            
            # Extract price data for additional indicators
            if 'klines' not in market_data or not market_data['klines']:
                return 'HOLD', 0.0, {'error': 'No kline data available'}
            
            klines = market_data['klines']
            df = pd.DataFrame(klines)
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float) if 'high' in df else df['close']
            df['low'] = df['low'].astype(float) if 'low' in df else df['close']
            
            # Calculate Bollinger Bands
            bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(df['close'], self.bb_period, self.bb_std)
            current_price = df['close'].iloc[-1]
            
            # Bollinger Band signal
            bb_signal = 'HOLD'
            bb_confidence = 0.0
            
            if current_price < bb_lower.iloc[-1]:
                bb_signal = 'BUY'
                bb_confidence = (bb_lower.iloc[-1] - current_price) / bb_lower.iloc[-1]
            elif current_price > bb_upper.iloc[-1]:
                bb_signal = 'SELL'
                bb_confidence = (current_price - bb_upper.iloc[-1]) / bb_upper.iloc[-1]
            else:
                # Position within bands
                bb_position = (current_price - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1])
                if bb_position < 0.3:
                    bb_signal = 'BUY'
                    bb_confidence = 0.3
                elif bb_position > 0.7:
                    bb_signal = 'SELL'
                    bb_confidence = 0.3
            
            # Volume analysis
            volume_profile = self.calculate_volume_profile(df)
            
            # Combine signals
            signals = {
                'rsi': (rsi_signal, rsi_confidence * self.weight_rsi),
                'ma': (ma_signal, ma_confidence * self.weight_ma),
                'bb': (bb_signal, bb_confidence * 0.2)  # Lower weight for BB
            }
            
            # Count agreeing indicators
            buy_score = sum(weight for signal, weight in signals.values() if signal == 'BUY')
            sell_score = sum(weight for signal, weight in signals.values() if signal == 'SELL')
            
            buy_count = sum(1 for signal, _ in signals.values() if signal == 'BUY')
            sell_count = sum(1 for signal, _ in signals.values() if signal == 'SELL')
            
            # Determine final signal
            final_signal = 'HOLD'
            final_confidence = 0.0
            
            if self.require_confirmation:
                # Require multiple indicators to agree
                if buy_count >= self.min_indicators_agree:
                    final_signal = 'BUY'
                    final_confidence = buy_score / sum(self.weight_rsi, self.weight_ma, 0.2)
                elif sell_count >= self.min_indicators_agree:
                    final_signal = 'SELL'
                    final_confidence = sell_score / sum(self.weight_rsi, self.weight_ma, 0.2)
            else:
                # Use weighted average
                if buy_score > sell_score and buy_score > 0.3:
                    final_signal = 'BUY'
                    final_confidence = buy_score
                elif sell_score > buy_score and sell_score > 0.3:
                    final_signal = 'SELL'
                    final_confidence = sell_score
            
            # Adjust confidence based on volume
            if volume_profile['volume_strength'] > 0:
                final_confidence = min(final_confidence * (1 + volume_profile['volume_strength'] * self.weight_volume), 1.0)
            
            # Calculate market strength
            market_strength = self.calculate_market_strength(df, rsi_meta, ma_meta)
            
            # Prepare metadata
            metadata = {
                'rsi': rsi_meta,
                'ma': ma_meta,
                'bb': {
                    'upper': round(bb_upper.iloc[-1], 2),
                    'middle': round(bb_middle.iloc[-1], 2),
                    'lower': round(bb_lower.iloc[-1], 2),
                    'position': round((current_price - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1]), 2)
                },
                'volume': volume_profile,
                'signals': {
                    'rsi': rsi_signal,
                    'ma': ma_signal,
                    'bb': bb_signal
                },
                'scores': {
                    'buy': round(buy_score, 3),
                    'sell': round(sell_score, 3)
                },
                'market_strength': round(market_strength, 2),
                'indicators_agree': max(buy_count, sell_count)
            }
            
            # Store last signal
            self.last_signal = final_signal
            self.last_signal_time = pd.Timestamp.now()
            
            return final_signal, final_confidence, metadata
            
        except Exception as e:
            logger.error(f"Error in combined analysis: {e}")
            return 'HOLD', 0.0, {'error': str(e)}
    
    def calculate_market_strength(self, df: pd.DataFrame, rsi_meta: Dict, ma_meta: Dict) -> float:
        """Calculate overall market strength"""
        strength_factors = []
        
        # RSI strength
        rsi_value = rsi_meta.get('rsi', 50)
        if rsi_value < 30 or rsi_value > 70:
            strength_factors.append(1.0)  # Strong signal
        elif rsi_value < 40 or rsi_value > 60:
            strength_factors.append(0.5)  # Moderate signal
        else:
            strength_factors.append(0.0)  # Neutral
        
        # Trend strength from MA
        strength_factors.append(ma_meta.get('trend_strength', 0.5))
        
        # Price momentum
        returns = df['close'].pct_change()
        recent_momentum = returns.tail(5).mean()
        strength_factors.append(min(abs(recent_momentum) * 10, 1.0))
        
        # Average strength
        return np.mean(strength_factors)
    
    def should_enter_position(self, signal: str, confidence: float, current_position: Optional[Dict]) -> bool:
        """Determine if should enter position based on combined strategy rules"""
        # Don't enter if already have position
        if current_position:
            return False
        
        # Higher confidence threshold for combined strategy
        min_conf = max(self.min_confidence, 0.65)
        if confidence < min_conf:
            return False
        
        # Only enter on BUY or SELL signals
        if signal == 'HOLD':
            return False
        
        return True
    
    def should_exit_position(self, current_position: Dict, market_data: Dict[str, Any]) -> bool:
        """Determine if should exit position based on combined strategy rules"""
        if not current_position:
            return False
        
        # Analyze current market
        signal, confidence, metadata = self.analyze(market_data)
        
        position_side = current_position.get('side')
        
        # Exit on strong opposite signal with multiple indicators agreeing
        indicators_agree = metadata.get('indicators_agree', 0)
        
        if position_side == 'Buy':
            if signal == 'SELL' and confidence > 0.6 and indicators_agree >= 2:
                return True
        elif position_side == 'Sell':
            if signal == 'BUY' and confidence > 0.6 and indicators_agree >= 2:
                return True
        
        # Exit if market strength weakens
        if metadata.get('market_strength', 0) < 0.2:
            return True
        
        # Check individual strategy exit conditions
        rsi_exit = self.rsi_strategy.should_exit_position(current_position, market_data)
        ma_exit = self.ma_strategy.should_exit_position(current_position, market_data)
        
        # Exit if both sub-strategies agree
        if rsi_exit and ma_exit:
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
            'weight_rsi': self.weight_rsi,
            'weight_ma': self.weight_ma,
            'weight_volume': self.weight_volume,
            'require_confirmation': self.require_confirmation,
            'min_indicators_agree': self.min_indicators_agree,
            'bb_period': self.bb_period,
            'bb_std': self.bb_std,
            'sub_strategies': {
                'rsi': self.rsi_strategy.get_config(),
                'ma': self.ma_strategy.get_config()
            }
        })
        return config