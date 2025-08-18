"""
Risk Management System
Handles position sizing, risk calculations, and safety checks
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)

class RiskManager:
    """Advanced risk management system"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Risk parameters (configurable)
        self.max_risk_per_trade = self.config.get('max_risk_per_trade', 0.02)  # 2% default
        self.max_risk_total = self.config.get('max_risk_total', 0.06)  # 6% total exposure
        self.max_leverage = self.config.get('max_leverage', 10)
        self.min_risk_reward_ratio = self.config.get('min_risk_reward_ratio', 1.5)
        self.max_daily_loss = self.config.get('max_daily_loss', 0.05)  # 5% daily loss limit
        self.max_positions = self.config.get('max_positions', 3)
        self.cooldown_after_loss = self.config.get('cooldown_minutes', 30)  # Minutes to wait after loss
        
        # Tracking
        self.daily_pnl = 0
        self.daily_trades = 0
        self.last_loss_time = None
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        
    def calculate_position_size(self, 
                               balance: float, 
                               entry_price: float, 
                               stop_loss_price: float,
                               leverage: int = 1) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate optimal position size based on risk parameters
        
        Returns:
            Tuple of (position_size, risk_metrics)
        """
        try:
            # Calculate risk distance
            risk_distance = abs(entry_price - stop_loss_price) / entry_price
            
            # Calculate maximum position value based on risk
            max_position_value = (balance * self.max_risk_per_trade) / risk_distance
            
            # Apply leverage
            max_position_value_with_leverage = max_position_value * min(leverage, self.max_leverage)
            
            # Calculate position size in base currency
            position_size = max_position_value_with_leverage / entry_price
            
            # Calculate risk metrics
            risk_amount = balance * self.max_risk_per_trade
            potential_loss = position_size * abs(entry_price - stop_loss_price)
            risk_percentage = (potential_loss / balance) * 100
            
            metrics = {
                'position_size': round(position_size, 8),
                'position_value': position_size * entry_price,
                'risk_amount': risk_amount,
                'potential_loss': potential_loss,
                'risk_percentage': risk_percentage,
                'leverage_used': leverage,
                'risk_distance': risk_distance * 100,  # As percentage
                'margin_required': (position_size * entry_price) / leverage
            }
            
            logger.info(f"Position size calculated: {position_size:.8f} | Risk: {risk_percentage:.2f}%")
            
            return position_size, metrics
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0, {}
    
    def validate_trade(self, 
                       balance: float,
                       current_positions: list,
                       proposed_trade: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate if a trade should be allowed based on risk rules
        
        Returns:
            Tuple of (is_valid, reason)
        """
        # Check cooldown period after loss
        if self.last_loss_time:
            time_since_loss = datetime.now() - self.last_loss_time
            if time_since_loss < timedelta(minutes=self.cooldown_after_loss):
                remaining = self.cooldown_after_loss - (time_since_loss.seconds // 60)
                return False, f"Cooldown period active. Wait {remaining} minutes"
        
        # Check max positions
        if len(current_positions) >= self.max_positions:
            return False, f"Maximum positions ({self.max_positions}) reached"
        
        # Check daily loss limit
        daily_loss_percent = abs(self.daily_pnl / balance) if self.daily_pnl < 0 else 0
        if daily_loss_percent >= self.max_daily_loss:
            return False, f"Daily loss limit ({self.max_daily_loss*100}%) reached"
        
        # Check total exposure
        total_exposure = sum(p.get('size', 0) * p.get('markPrice', 0) for p in current_positions)
        proposed_exposure = proposed_trade.get('size', 0) * proposed_trade.get('price', 0)
        total_risk_percent = (total_exposure + proposed_exposure) / balance
        
        if total_risk_percent > self.max_risk_total:
            return False, f"Total exposure ({total_risk_percent*100:.1f}%) exceeds limit ({self.max_risk_total*100}%)"
        
        # Check consecutive losses
        if self.consecutive_losses >= 3:
            return False, "3 consecutive losses. Trading paused for review"
        
        # Check risk/reward ratio
        if 'take_profit' in proposed_trade and 'stop_loss' in proposed_trade:
            entry = proposed_trade['price']
            tp = proposed_trade['take_profit']
            sl = proposed_trade['stop_loss']
            
            risk = abs(entry - sl)
            reward = abs(tp - entry)
            rr_ratio = reward / risk if risk > 0 else 0
            
            if rr_ratio < self.min_risk_reward_ratio:
                return False, f"Risk/Reward ratio ({rr_ratio:.2f}) below minimum ({self.min_risk_reward_ratio})"
        
        return True, "Trade validated"
    
    def calculate_stop_loss(self, 
                           entry_price: float,
                           side: str,
                           atr: float = None,
                           support_resistance: list = None) -> float:
        """
        Calculate dynamic stop loss based on market conditions
        """
        # Base stop loss percentage
        base_stop = 0.02  # 2%
        
        # Adjust based on ATR if available
        if atr:
            atr_multiplier = 2.0
            atr_stop = (atr * atr_multiplier) / entry_price
            base_stop = max(base_stop, atr_stop)
        
        # Calculate stop loss price
        if side == 'Buy':
            stop_loss = entry_price * (1 - base_stop)
            
            # Adjust to support level if available
            if support_resistance:
                supports = [s for s in support_resistance if s < entry_price]
                if supports:
                    nearest_support = max(supports)
                    # Place stop just below support
                    stop_loss = min(stop_loss, nearest_support * 0.995)
        else:
            stop_loss = entry_price * (1 + base_stop)
            
            # Adjust to resistance level if available
            if support_resistance:
                resistances = [r for r in support_resistance if r > entry_price]
                if resistances:
                    nearest_resistance = min(resistances)
                    # Place stop just above resistance
                    stop_loss = max(stop_loss, nearest_resistance * 1.005)
        
        return round(stop_loss, 2)
    
    def calculate_take_profit(self,
                             entry_price: float,
                             stop_loss: float,
                             side: str,
                             risk_reward_ratio: float = None) -> float:
        """
        Calculate take profit based on risk/reward ratio
        """
        rr_ratio = risk_reward_ratio or self.min_risk_reward_ratio
        
        risk_distance = abs(entry_price - stop_loss)
        reward_distance = risk_distance * rr_ratio
        
        if side == 'Buy':
            take_profit = entry_price + reward_distance
        else:
            take_profit = entry_price - reward_distance
        
        return round(take_profit, 2)
    
    def update_trade_result(self, pnl: float, is_win: bool):
        """Update tracking metrics after trade completion"""
        self.daily_pnl += pnl
        self.daily_trades += 1
        
        if is_win:
            self.consecutive_wins += 1
            self.consecutive_losses = 0
            self.last_loss_time = None
        else:
            self.consecutive_losses += 1
            self.consecutive_wins = 0
            self.last_loss_time = datetime.now()
        
        logger.info(f"Trade result updated: PnL={pnl:.2f}, Daily PnL={self.daily_pnl:.2f}")
    
    def get_risk_score(self, 
                      balance: float,
                      positions: list,
                      market_volatility: float = None) -> Dict[str, Any]:
        """
        Calculate overall risk score and metrics
        """
        # Calculate exposure
        total_exposure = sum(p.get('size', 0) * p.get('markPrice', 0) for p in positions)
        exposure_percent = (total_exposure / balance) * 100 if balance > 0 else 0
        
        # Calculate unrealized PnL
        total_unrealized_pnl = sum(p.get('unrealizedPnl', 0) for p in positions)
        unrealized_pnl_percent = (total_unrealized_pnl / balance) * 100 if balance > 0 else 0
        
        # Calculate risk score (0-100, higher is riskier)
        risk_score = 0
        
        # Factor 1: Exposure (0-40 points)
        risk_score += min(40, (exposure_percent / self.max_risk_total) * 40)
        
        # Factor 2: Daily loss (0-30 points)
        daily_loss_percent = abs(self.daily_pnl / balance) if self.daily_pnl < 0 else 0
        risk_score += min(30, (daily_loss_percent / self.max_daily_loss) * 30)
        
        # Factor 3: Consecutive losses (0-20 points)
        risk_score += min(20, self.consecutive_losses * 6.67)
        
        # Factor 4: Market volatility (0-10 points)
        if market_volatility:
            # Assuming volatility is normalized 0-1
            risk_score += min(10, market_volatility * 10)
        
        # Determine risk level
        if risk_score < 25:
            risk_level = 'LOW'
            risk_color = 'green'
        elif risk_score < 50:
            risk_level = 'MEDIUM'
            risk_color = 'yellow'
        elif risk_score < 75:
            risk_level = 'HIGH'
            risk_color = 'orange'
        else:
            risk_level = 'CRITICAL'
            risk_color = 'red'
        
        return {
            'risk_score': round(risk_score, 1),
            'risk_level': risk_level,
            'risk_color': risk_color,
            'total_exposure': total_exposure,
            'exposure_percent': round(exposure_percent, 2),
            'daily_pnl': round(self.daily_pnl, 2),
            'daily_pnl_percent': round((self.daily_pnl / balance) * 100, 2) if balance > 0 else 0,
            'unrealized_pnl': round(total_unrealized_pnl, 2),
            'unrealized_pnl_percent': round(unrealized_pnl_percent, 2),
            'consecutive_losses': self.consecutive_losses,
            'consecutive_wins': self.consecutive_wins,
            'daily_trades': self.daily_trades,
            'positions_count': len(positions),
            'max_positions': self.max_positions,
            'can_trade': risk_score < 75 and len(positions) < self.max_positions
        }
    
    def reset_daily_metrics(self):
        """Reset daily tracking metrics"""
        self.daily_pnl = 0
        self.daily_trades = 0
        logger.info("Daily metrics reset")
    
    def get_position_health(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze health of an individual position
        """
        pnl = position.get('unrealizedPnl', 0)
        pnl_percent = position.get('unrealizedPnlPercent', 0)
        
        # Determine health status
        if pnl_percent > 5:
            status = 'EXCELLENT'
            color = 'green'
            action = 'Consider trailing stop'
        elif pnl_percent > 2:
            status = 'GOOD'
            color = 'lightgreen'
            action = 'Monitor closely'
        elif pnl_percent > -1:
            status = 'NEUTRAL'
            color = 'gray'
            action = 'Watch for reversal'
        elif pnl_percent > -3:
            status = 'WARNING'
            color = 'orange'
            action = 'Consider exit'
        else:
            status = 'CRITICAL'
            color = 'red'
            action = 'Exit recommended'
        
        return {
            'status': status,
            'color': color,
            'action': action,
            'pnl': pnl,
            'pnl_percent': pnl_percent
        }