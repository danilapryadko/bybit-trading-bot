"""
Base Strategy Class
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseStrategy(ABC):
    """Base class for all trading strategies"""
    
    def __init__(self, symbol: str, params: Dict[str, Any] = None):
        self.symbol = symbol
        self.params = params or {}
        self.name = self.__class__.__name__
        self.is_active = False
        self.last_signal = None
        self.last_signal_time = None
        self.position = None
        
        # Default parameters
        self.leverage = self.params.get('leverage', 10)
        self.position_size = self.params.get('position_size', 100)  # in USDT
        self.stop_loss_percent = self.params.get('stop_loss_percent', 2.0)
        self.take_profit_percent = self.params.get('take_profit_percent', 3.0)
        self.min_confidence = self.params.get('min_confidence', 0.6)
        
    @abstractmethod
    def analyze(self, market_data: Dict[str, Any]) -> Tuple[str, float, Dict[str, Any]]:
        """
        Analyze market data and generate trading signal
        
        Args:
            market_data: Dictionary containing price, volume, indicators, etc.
            
        Returns:
            Tuple of (signal, confidence, metadata)
            - signal: 'BUY', 'SELL', or 'HOLD'
            - confidence: float between 0 and 1
            - metadata: additional information about the signal
        """
        pass
    
    @abstractmethod
    def should_enter_position(self, signal: str, confidence: float, current_position: Optional[Dict]) -> bool:
        """
        Determine if strategy should enter a position
        
        Args:
            signal: Current trading signal
            confidence: Signal confidence
            current_position: Current open position if any
            
        Returns:
            Boolean indicating whether to enter position
        """
        pass
    
    @abstractmethod
    def should_exit_position(self, current_position: Dict, market_data: Dict[str, Any]) -> bool:
        """
        Determine if strategy should exit current position
        
        Args:
            current_position: Current open position
            market_data: Current market data
            
        Returns:
            Boolean indicating whether to exit position
        """
        pass
    
    def calculate_position_size(self, price: float, balance: float) -> float:
        """Calculate position size based on available balance and risk management"""
        # Use percentage of balance or fixed amount
        if self.params.get('use_percentage', False):
            position_value = balance * (self.params.get('position_percent', 10) / 100)
        else:
            position_value = min(self.position_size, balance * 0.9)  # Max 90% of balance
        
        qty = position_value / price
        return round(qty, 3)
    
    def calculate_stop_loss(self, entry_price: float, side: str) -> float:
        """Calculate stop loss price"""
        if side == 'Buy':
            return round(entry_price * (1 - self.stop_loss_percent / 100), 2)
        else:
            return round(entry_price * (1 + self.stop_loss_percent / 100), 2)
    
    def calculate_take_profit(self, entry_price: float, side: str) -> float:
        """Calculate take profit price"""
        if side == 'Buy':
            return round(entry_price * (1 + self.take_profit_percent / 100), 2)
        else:
            return round(entry_price * (1 - self.take_profit_percent / 100), 2)
    
    def get_risk_reward_ratio(self) -> float:
        """Calculate risk/reward ratio"""
        return self.take_profit_percent / self.stop_loss_percent
    
    def validate_signal(self, signal: str, confidence: float) -> bool:
        """Validate trading signal before execution"""
        # Check confidence threshold
        if confidence < self.min_confidence:
            logger.info(f"Signal confidence {confidence:.2%} below threshold {self.min_confidence:.2%}")
            return False
        
        # Check for valid signal
        if signal not in ['BUY', 'SELL', 'HOLD']:
            logger.warning(f"Invalid signal: {signal}")
            return False
        
        # Additional validation can be added here
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert strategy to dictionary for serialization"""
        return {
            'name': self.name,
            'symbol': self.symbol,
            'is_active': self.is_active,
            'params': self.params,
            'last_signal': self.last_signal,
            'last_signal_time': self.last_signal_time.isoformat() if self.last_signal_time else None,
            'leverage': self.leverage,
            'position_size': self.position_size,
            'stop_loss_percent': self.stop_loss_percent,
            'take_profit_percent': self.take_profit_percent,
            'min_confidence': self.min_confidence,
            'risk_reward_ratio': self.get_risk_reward_ratio()
        }