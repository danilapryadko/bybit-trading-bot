"""
Enhanced Risk Management System V2 for Bybit Trading Bot
Advanced position sizing, dynamic stops, and risk controls
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, asdict
import numpy as np
import pandas as pd
from collections import deque
import threading
import json

logger = logging.getLogger(__name__)


@dataclass
class RiskProfile:
    """Risk profile configuration"""
    name: str = "default"
    max_position_size: float = 10000.0  # Maximum position size in USDT
    max_leverage: float = 3.0  # Maximum leverage
    max_positions: int = 5  # Maximum concurrent positions
    max_daily_loss: float = 500.0  # Maximum daily loss in USDT
    max_drawdown: float = 0.15  # Maximum drawdown percentage (15%)
    risk_per_trade: float = 0.02  # Risk 2% per trade
    use_kelly_criterion: bool = True  # Use Kelly criterion for sizing
    kelly_fraction: float = 0.25  # Fraction of Kelly criterion to use
    correlation_limit: float = 0.7  # Maximum correlation between positions
    var_confidence: float = 0.95  # Value at Risk confidence level
    stop_loss_atr_multiplier: float = 2.0  # Stop loss distance in ATR units
    take_profit_ratio: float = 2.0  # Risk/reward ratio for take profit
    trailing_stop_activation: float = 0.01  # Activate trailing stop at 1% profit
    trailing_stop_distance: float = 0.005  # Trail by 0.5%


@dataclass
class Position:
    """Position tracking"""
    symbol: str
    side: str  # "long" or "short"
    entry_price: float
    current_price: float
    quantity: float
    leverage: float = 1.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    trailing_stop: float = 0.0
    trailing_activated: bool = False
    highest_price: float = 0.0  # For trailing stop
    lowest_price: float = 0.0  # For trailing stop
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    created_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_pnl(self) -> float:
        """Calculate current P&L"""
        if self.side == "long":
            self.unrealized_pnl = (self.current_price - self.entry_price) * self.quantity
        else:
            self.unrealized_pnl = (self.entry_price - self.current_price) * self.quantity
        return self.unrealized_pnl
    
    def calculate_risk(self) -> float:
        """Calculate position risk"""
        if self.stop_loss > 0:
            if self.side == "long":
                risk = (self.entry_price - self.stop_loss) * self.quantity
            else:
                risk = (self.stop_loss - self.entry_price) * self.quantity
            return abs(risk)
        return self.quantity * self.entry_price * 0.1  # Default 10% risk


class RiskManagerV2:
    """Enhanced risk management with advanced features"""
    
    def __init__(self, account_balance: float = 10000.0, risk_profile: Optional[RiskProfile] = None,
                 max_position_size: float = 0.2, max_daily_loss: float = 0.05, max_drawdown: float = 0.15):
        self.account_balance = account_balance
        self.initial_balance = account_balance
        self.risk_profile = risk_profile or RiskProfile()
        
        # Override with constructor params if provided
        self.max_position_size = max_position_size
        self.max_daily_loss = max_daily_loss
        self.max_drawdown = max_drawdown
        
        # Position tracking
        self.positions = {}  # symbol -> Position
        self.position_history = deque(maxlen=1000)
        self.daily_pnl = 0.0
        self.daily_reset_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
        
        # Performance metrics
        self.metrics = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "max_drawdown": 0.0,
            "current_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "kelly_percentage": 0.0,
            "var_daily": 0.0,
            "expected_shortfall": 0.0
        }
        
        # Market data for calculations
        self.market_data = {}  # symbol -> {atr, volatility, correlation}
        self.price_history = {}  # symbol -> deque of prices
        self.returns_history = deque(maxlen=252)  # Daily returns for Sharpe ratio
        
        # Threading lock for concurrent access
        self.lock = threading.Lock()
        
        logger.info(f"Risk Manager V2 initialized with balance: {account_balance}")
    
    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        market_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Calculate optimal position size using multiple methods"""
        try:
            # Basic risk-based position sizing
            risk_amount = self.account_balance * self.risk_profile.risk_per_trade
            price_risk = abs(entry_price - stop_loss)
            
            if price_risk == 0:
                logger.warning("Stop loss at entry price, using default risk")
                price_risk = entry_price * 0.02  # 2% default
            
            # Method 1: Fixed risk position sizing
            fixed_risk_size = risk_amount / price_risk
            
            # Method 2: Kelly Criterion (if enabled and data available)
            kelly_size = 0
            if self.risk_profile.use_kelly_criterion and market_data:
                kelly_size = self._calculate_kelly_size(symbol, market_data)
            
            # Method 3: Volatility-adjusted sizing
            volatility_size = self._calculate_volatility_adjusted_size(symbol, entry_price)
            
            # Method 4: Correlation-adjusted sizing
            correlation_adjustment = self._calculate_correlation_adjustment(symbol)
            
            # Combine methods
            if kelly_size > 0:
                # Use Kelly with safety fraction
                base_size = kelly_size * self.risk_profile.kelly_fraction
            else:
                # Use fixed risk method
                base_size = fixed_risk_size
            
            # Apply volatility adjustment
            if volatility_size > 0:
                base_size = min(base_size, volatility_size)
            
            # Apply correlation adjustment
            base_size *= correlation_adjustment
            
            # Apply position limits
            max_position_value = self.risk_profile.max_position_size
            max_size = max_position_value / entry_price
            
            # Consider existing positions
            current_exposure = self._calculate_total_exposure()
            available_balance = self.account_balance - current_exposure
            max_affordable = available_balance / entry_price
            
            # Final position size
            position_size = min(base_size, max_size, max_affordable)
            
            # Ensure minimum size
            min_size = 10.0 / entry_price  # Minimum $10 position
            if position_size < min_size:
                position_size = 0
            
            return {
                "position_size": position_size,
                "position_value": position_size * entry_price,
                "risk_amount": risk_amount,
                "methods": {
                    "fixed_risk": fixed_risk_size,
                    "kelly": kelly_size,
                    "volatility_adjusted": volatility_size,
                    "correlation_factor": correlation_adjustment
                },
                "risk_percentage": (risk_amount / self.account_balance) * 100,
                "leverage": (position_size * entry_price) / available_balance if available_balance > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return {"position_size": 0, "error": str(e)}
    
    def _calculate_kelly_size(self, symbol: str, market_data: Dict[str, Any]) -> float:
        """Calculate position size using Kelly Criterion"""
        try:
            # Get historical win rate and average win/loss
            symbol_history = [p for p in self.position_history if p.symbol == symbol]
            
            if len(symbol_history) < 10:
                # Not enough history, return 0
                return 0
            
            wins = [p for p in symbol_history if p.realized_pnl > 0]
            losses = [p for p in symbol_history if p.realized_pnl <= 0]
            
            if not wins or not losses:
                return 0
            
            win_rate = len(wins) / len(symbol_history)
            avg_win = sum(p.realized_pnl for p in wins) / len(wins)
            avg_loss = abs(sum(p.realized_pnl for p in losses) / len(losses))
            
            if avg_loss == 0:
                return 0
            
            # Kelly formula: f = (p * b - q) / b
            # where p = win probability, q = loss probability, b = win/loss ratio
            b = avg_win / avg_loss
            p = win_rate
            q = 1 - p
            
            kelly_percentage = (p * b - q) / b
            
            # Ensure Kelly percentage is positive and reasonable
            kelly_percentage = max(0, min(kelly_percentage, 0.25))  # Cap at 25%
            
            # Store for metrics
            self.metrics["kelly_percentage"] = kelly_percentage
            
            # Calculate size based on Kelly percentage
            kelly_value = self.account_balance * kelly_percentage
            entry_price = market_data.get("price", 1)
            
            return kelly_value / entry_price
            
        except Exception as e:
            logger.error(f"Error calculating Kelly size: {e}")
            return 0
    
    def _calculate_volatility_adjusted_size(self, symbol: str, entry_price: float) -> float:
        """Calculate position size adjusted for volatility"""
        try:
            if symbol not in self.market_data:
                return 0
            
            volatility = self.market_data[symbol].get("volatility", 0)
            atr = self.market_data[symbol].get("atr", 0)
            
            if volatility == 0 or atr == 0:
                return 0
            
            # Target volatility (e.g., 1% daily)
            target_volatility = 0.01
            
            # Adjust position size based on volatility
            volatility_scalar = target_volatility / volatility
            
            # Use ATR for position sizing
            atr_risk = atr * self.risk_profile.stop_loss_atr_multiplier
            risk_amount = self.account_balance * self.risk_profile.risk_per_trade
            
            position_size = (risk_amount / atr_risk) * volatility_scalar
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating volatility adjusted size: {e}")
            return 0
    
    def _calculate_correlation_adjustment(self, symbol: str) -> float:
        """Calculate correlation adjustment factor"""
        try:
            if not self.positions:
                return 1.0
            
            # Check correlation with existing positions
            max_correlation = 0
            for existing_symbol in self.positions:
                if existing_symbol == symbol:
                    continue
                
                correlation = self._get_correlation(symbol, existing_symbol)
                max_correlation = max(max_correlation, abs(correlation))
            
            # Reduce size if correlation is high
            if max_correlation > self.risk_profile.correlation_limit:
                adjustment = 1.0 - (max_correlation - self.risk_profile.correlation_limit)
                return max(0.2, adjustment)  # Minimum 20% of original size
            
            return 1.0
            
        except Exception as e:
            logger.error(f"Error calculating correlation adjustment: {e}")
            return 1.0
    
    def _get_correlation(self, symbol1: str, symbol2: str) -> float:
        """Get correlation between two symbols"""
        try:
            if symbol1 not in self.price_history or symbol2 not in self.price_history:
                return 0
            
            prices1 = list(self.price_history[symbol1])
            prices2 = list(self.price_history[symbol2])
            
            if len(prices1) < 20 or len(prices2) < 20:
                return 0
            
            # Calculate returns
            returns1 = pd.Series(prices1).pct_change().dropna()
            returns2 = pd.Series(prices2).pct_change().dropna()
            
            # Align series
            min_len = min(len(returns1), len(returns2))
            returns1 = returns1[-min_len:]
            returns2 = returns2[-min_len:]
            
            # Calculate correlation
            correlation = returns1.corr(returns2)
            
            return correlation if not pd.isna(correlation) else 0
            
        except Exception as e:
            logger.error(f"Error calculating correlation: {e}")
            return 0
    
    def calculate_stop_loss(
        self,
        symbol: str,
        entry_price: float,
        side: str,
        atr: Optional[float] = None
    ) -> float:
        """Calculate dynamic stop loss"""
        try:
            # Method 1: ATR-based stop loss
            if atr:
                stop_distance = atr * self.risk_profile.stop_loss_atr_multiplier
            else:
                # Default percentage-based stop
                stop_distance = entry_price * 0.02  # 2% default
            
            # Adjust for side
            if side == "long":
                stop_loss = entry_price - stop_distance
            else:
                stop_loss = entry_price + stop_distance
            
            # Ensure stop loss is valid
            if side == "long":
                stop_loss = max(stop_loss, entry_price * 0.95)  # Max 5% stop
            else:
                stop_loss = min(stop_loss, entry_price * 1.05)  # Max 5% stop
            
            return stop_loss
            
        except Exception as e:
            logger.error(f"Error calculating stop loss: {e}")
            # Return default stop
            if side == "long":
                return entry_price * 0.98
            else:
                return entry_price * 1.02
    
    def calculate_take_profit(
        self,
        entry_price: float,
        stop_loss: float,
        side: str
    ) -> float:
        """Calculate take profit based on risk/reward ratio"""
        try:
            risk = abs(entry_price - stop_loss)
            reward = risk * self.risk_profile.take_profit_ratio
            
            if side == "long":
                take_profit = entry_price + reward
            else:
                take_profit = entry_price - reward
            
            return take_profit
            
        except Exception as e:
            logger.error(f"Error calculating take profit: {e}")
            # Return default take profit
            if side == "long":
                return entry_price * 1.03
            else:
                return entry_price * 0.97
    
    def update_trailing_stop(self, position: Position, current_price: float) -> Optional[float]:
        """Update trailing stop for a position"""
        try:
            # Check if trailing stop should be activated
            if not position.trailing_activated:
                if position.side == "long":
                    profit_pct = (current_price - position.entry_price) / position.entry_price
                    if profit_pct >= self.risk_profile.trailing_stop_activation:
                        position.trailing_activated = True
                        position.highest_price = current_price
                        position.trailing_stop = current_price * (1 - self.risk_profile.trailing_stop_distance)
                        logger.info(f"Trailing stop activated for {position.symbol} at {position.trailing_stop}")
                else:  # short
                    profit_pct = (position.entry_price - current_price) / position.entry_price
                    if profit_pct >= self.risk_profile.trailing_stop_activation:
                        position.trailing_activated = True
                        position.lowest_price = current_price
                        position.trailing_stop = current_price * (1 + self.risk_profile.trailing_stop_distance)
                        logger.info(f"Trailing stop activated for {position.symbol} at {position.trailing_stop}")
            
            # Update trailing stop if activated
            if position.trailing_activated:
                if position.side == "long":
                    if current_price > position.highest_price:
                        position.highest_price = current_price
                        new_stop = current_price * (1 - self.risk_profile.trailing_stop_distance)
                        if new_stop > position.trailing_stop:
                            position.trailing_stop = new_stop
                            return new_stop
                else:  # short
                    if current_price < position.lowest_price:
                        position.lowest_price = current_price
                        new_stop = current_price * (1 + self.risk_profile.trailing_stop_distance)
                        if new_stop < position.trailing_stop:
                            position.trailing_stop = new_stop
                            return new_stop
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating trailing stop: {e}")
            return None
    
    def check_risk_limits(self) -> Dict[str, Any]:
        """Check if current risk levels are within limits"""
        try:
            checks = {
                "passed": True,
                "warnings": [],
                "errors": []
            }
            
            # Check maximum positions
            if len(self.positions) >= self.risk_profile.max_positions:
                checks["errors"].append(f"Maximum positions reached: {len(self.positions)}/{self.risk_profile.max_positions}")
                checks["passed"] = False
            
            # Check daily loss
            if abs(self.daily_pnl) >= self.risk_profile.max_daily_loss:
                checks["errors"].append(f"Daily loss limit reached: ${abs(self.daily_pnl):.2f}")
                checks["passed"] = False
            
            # Check drawdown
            current_value = self.account_balance + self._calculate_total_unrealized_pnl()
            drawdown = (self.initial_balance - current_value) / self.initial_balance
            if drawdown >= self.risk_profile.max_drawdown:
                checks["errors"].append(f"Maximum drawdown reached: {drawdown:.2%}")
                checks["passed"] = False
            
            # Check leverage
            total_exposure = self._calculate_total_exposure()
            current_leverage = total_exposure / self.account_balance if self.account_balance > 0 else 0
            if current_leverage > self.risk_profile.max_leverage:
                checks["warnings"].append(f"High leverage: {current_leverage:.2f}x")
            
            # Check correlation
            if self._check_high_correlation():
                checks["warnings"].append("High correlation detected between positions")
            
            return checks
            
        except Exception as e:
            logger.error(f"Error checking risk limits: {e}")
            return {"passed": False, "error": str(e)}
    
    def calculate_var(self, confidence_level: Optional[float] = None) -> float:
        """Calculate Value at Risk"""
        try:
            if not self.returns_history:
                return 0
            
            confidence = confidence_level or self.risk_profile.var_confidence
            returns = np.array(list(self.returns_history))
            
            # Calculate VaR using historical simulation
            var_percentile = (1 - confidence) * 100
            var = np.percentile(returns, var_percentile)
            
            # Convert to dollar amount
            var_amount = abs(var * self.account_balance)
            
            self.metrics["var_daily"] = var_amount
            
            return var_amount
            
        except Exception as e:
            logger.error(f"Error calculating VaR: {e}")
            return 0
    
    def calculate_expected_shortfall(self) -> float:
        """Calculate Expected Shortfall (Conditional VaR)"""
        try:
            if not self.returns_history:
                return 0
            
            returns = np.array(list(self.returns_history))
            var_percentile = (1 - self.risk_profile.var_confidence) * 100
            var = np.percentile(returns, var_percentile)
            
            # Calculate average of returns worse than VaR
            worse_returns = returns[returns <= var]
            if len(worse_returns) > 0:
                es = np.mean(worse_returns)
                es_amount = abs(es * self.account_balance)
                self.metrics["expected_shortfall"] = es_amount
                return es_amount
            
            return 0
            
        except Exception as e:
            logger.error(f"Error calculating Expected Shortfall: {e}")
            return 0
    
    def update_market_data(self, symbol: str, data: Dict[str, Any]):
        """Update market data for risk calculations"""
        with self.lock:
            if symbol not in self.market_data:
                self.market_data[symbol] = {}
            
            self.market_data[symbol].update(data)
            
            # Update price history
            if "price" in data:
                if symbol not in self.price_history:
                    self.price_history[symbol] = deque(maxlen=100)
                self.price_history[symbol].append(data["price"])
    
    def add_position(self, position: Position):
        """Add a new position"""
        with self.lock:
            self.positions[position.symbol] = position
            self.metrics["total_trades"] += 1
            logger.info(f"Position added: {position.symbol} {position.side} @ {position.entry_price}")
    
    def close_position(self, symbol: str, exit_price: float):
        """Close a position"""
        with self.lock:
            if symbol not in self.positions:
                logger.error(f"Position not found: {symbol}")
                return
            
            position = self.positions[symbol]
            position.current_price = exit_price
            position.calculate_pnl()
            position.realized_pnl = position.unrealized_pnl
            
            # Update metrics
            if position.realized_pnl > 0:
                self.metrics["winning_trades"] += 1
            else:
                self.metrics["losing_trades"] += 1
            
            self.metrics["total_pnl"] += position.realized_pnl
            self.daily_pnl += position.realized_pnl
            self.account_balance += position.realized_pnl
            
            # Add to history and remove from active
            self.position_history.append(position)
            del self.positions[symbol]
            
            # Update performance metrics
            self._update_performance_metrics()
            
            logger.info(f"Position closed: {symbol} P&L: ${position.realized_pnl:.2f}")
    
    def _calculate_total_exposure(self) -> float:
        """Calculate total exposure across all positions"""
        total = 0
        for position in self.positions.values():
            total += position.quantity * position.entry_price * position.leverage
        return total
    
    def _calculate_total_unrealized_pnl(self) -> float:
        """Calculate total unrealized P&L"""
        total = 0
        for position in self.positions.values():
            position.calculate_pnl()
            total += position.unrealized_pnl
        return total
    
    def _check_high_correlation(self) -> bool:
        """Check if positions have high correlation"""
        if len(self.positions) < 2:
            return False
        
        symbols = list(self.positions.keys())
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                correlation = self._get_correlation(symbols[i], symbols[j])
                if abs(correlation) > self.risk_profile.correlation_limit:
                    return True
        return False
    
    def _update_performance_metrics(self):
        """Update performance metrics"""
        try:
            # Calculate win rate
            total = self.metrics["winning_trades"] + self.metrics["losing_trades"]
            if total > 0:
                self.metrics["win_rate"] = self.metrics["winning_trades"] / total
            
            # Calculate profit factor
            wins = [p.realized_pnl for p in self.position_history if p.realized_pnl > 0]
            losses = [abs(p.realized_pnl) for p in self.position_history if p.realized_pnl < 0]
            
            if losses:
                total_wins = sum(wins) if wins else 0
                total_losses = sum(losses)
                self.metrics["profit_factor"] = total_wins / total_losses if total_losses > 0 else 0
            
            # Calculate Sharpe ratio (simplified daily)
            if len(self.returns_history) > 30:
                returns = np.array(list(self.returns_history))
                avg_return = np.mean(returns)
                std_return = np.std(returns)
                if std_return > 0:
                    self.metrics["sharpe_ratio"] = (avg_return * 252) / (std_return * np.sqrt(252))
            
            # Update drawdown
            current_value = self.account_balance
            peak_value = max(self.initial_balance, current_value)
            self.metrics["current_drawdown"] = (peak_value - current_value) / peak_value
            self.metrics["max_drawdown"] = max(self.metrics["max_drawdown"], self.metrics["current_drawdown"])
            
        except Exception as e:
            logger.error(f"Error updating performance metrics: {e}")
    
    def reset_daily_metrics(self):
        """Reset daily metrics"""
        current_time = datetime.now(timezone.utc)
        if current_time.date() > self.daily_reset_time.date():
            self.daily_pnl = 0
            self.daily_reset_time = current_time.replace(hour=0, minute=0, second=0)
            
            # Add daily return to history
            if self.account_balance > 0:
                daily_return = (self.account_balance - self.initial_balance) / self.initial_balance
                self.returns_history.append(daily_return)
            
            logger.info("Daily metrics reset")
    
    def validate_order(self, symbol: str, side: str, quantity: float, price: float) -> Tuple[bool, str]:
        """Validate an order against risk limits"""
        try:
            # Check if we have too many positions
            if len(self.positions) >= self.risk_profile.max_positions:
                return False, f"Maximum positions ({self.risk_profile.max_positions}) reached"
            
            # Calculate order value
            order_value = quantity * price
            
            # Check position size limit
            max_size = self.account_balance * self.max_position_size
            if order_value > max_size:
                return False, f"Order value ${order_value:.2f} exceeds max position size ${max_size:.2f}"
            
            # Check daily loss limit
            if abs(self.daily_pnl) >= self.account_balance * self.max_daily_loss:
                return False, f"Daily loss limit reached (${abs(self.daily_pnl):.2f})"
            
            # Check drawdown limit
            current_dd = (self.initial_balance - self.account_balance) / self.initial_balance
            if current_dd >= self.max_drawdown:
                return False, f"Maximum drawdown reached ({current_dd:.1%})"
            
            # Check correlation with existing positions
            if symbol in self.positions:
                return False, f"Position already exists for {symbol}"
            
            # All checks passed
            return True, "Order validated successfully"
            
        except Exception as e:
            logger.error(f"Error validating order: {e}")
            return False, f"Validation error: {str(e)}"
    
    def calculate_position_size(self, balance: float, price: float, risk_percent: float) -> float:
        """Calculate position size based on risk percentage"""
        risk_amount = balance * (risk_percent / 100)
        position_size = risk_amount / price
        
        # Apply max position size limit
        max_size = balance * self.max_position_size / price
        return min(position_size, max_size)
    
    def check_risk_limits(self, balance: float) -> bool:
        """Check if risk limits are exceeded"""
        # Check daily loss
        if abs(self.daily_pnl) >= balance * self.max_daily_loss:
            return False
        
        # Check drawdown
        current_dd = (self.initial_balance - balance) / self.initial_balance
        if current_dd >= self.max_drawdown:
            return False
        
        return True
    
    def update_daily_pnl(self, pnl: float):
        """Update daily P&L tracking"""
        self.daily_pnl += pnl
    
    def update_settings(self, max_position_size: float = None, max_daily_loss: float = None, 
                       max_drawdown: float = None):
        """Update risk management settings"""
        if max_position_size is not None:
            self.max_position_size = max_position_size
            self.risk_profile.max_position_size = max_position_size
        
        if max_daily_loss is not None:
            self.max_daily_loss = max_daily_loss
            self.risk_profile.max_daily_loss = max_daily_loss
        
        if max_drawdown is not None:
            self.max_drawdown = max_drawdown
            self.risk_profile.max_drawdown = max_drawdown
    
    def get_risk_report(self) -> Dict[str, Any]:
        """Generate comprehensive risk report"""
        self._update_performance_metrics()
        
        return {
            "account": {
                "balance": self.account_balance,
                "initial_balance": self.initial_balance,
                "total_pnl": self.metrics["total_pnl"],
                "daily_pnl": self.daily_pnl,
                "unrealized_pnl": self._calculate_total_unrealized_pnl()
            },
            "positions": {
                "count": len(self.positions),
                "total_exposure": self._calculate_total_exposure(),
                "leverage": self._calculate_total_exposure() / self.account_balance if self.account_balance > 0 else 0
            },
            "performance": {
                "win_rate": self.metrics["win_rate"],
                "profit_factor": self.metrics["profit_factor"],
                "sharpe_ratio": self.metrics["sharpe_ratio"],
                "max_drawdown": self.metrics["max_drawdown"],
                "current_drawdown": self.metrics["current_drawdown"]
            },
            "risk_metrics": {
                "var_daily": self.metrics["var_daily"],
                "expected_shortfall": self.metrics["expected_shortfall"],
                "kelly_percentage": self.metrics["kelly_percentage"]
            },
            "limits": {
                "max_positions": self.risk_profile.max_positions,
                "max_daily_loss": self.risk_profile.max_daily_loss,
                "max_drawdown": self.risk_profile.max_drawdown,
                "max_leverage": self.risk_profile.max_leverage
            }
        }