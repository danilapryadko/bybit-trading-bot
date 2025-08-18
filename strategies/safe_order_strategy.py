"""
Safe Order (DCA) Strategy with Grid Trading
Implements Dollar Cost Averaging with safety orders for risk management
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class SafeOrderConfig:
    """Configuration for Safe Orders (DCA)"""
    # Base order settings
    base_order_size: float = 50.0  # USDT for initial order
    
    # Safety order settings
    safety_order_size: float = 100.0  # USDT for first safety order
    max_safety_orders: int = 5  # Maximum number of safety orders
    safety_order_volume_scale: float = 1.5  # Multiplier for each subsequent SO
    safety_order_step_scale: float = 1.2  # Price deviation multiplier
    safety_order_price_deviation: float = 1.0  # % price drop for first SO
    
    # Take profit settings
    take_profit: float = 2.0  # % take profit
    trailing_take_profit: bool = True  # Enable trailing TP
    trailing_deviation: float = 0.5  # % deviation for trailing
    
    # Grid settings (optional)
    use_grid: bool = True
    grid_levels: int = 10
    grid_spacing: float = 0.5  # % between grid levels
    
    # Risk management
    max_position_size: float = 1000.0  # Maximum USDT in position
    stop_loss: Optional[float] = 10.0  # % stop loss (optional)
    
    # Strategy behavior
    martingale_enabled: bool = False  # Double down on losses
    compound_profits: bool = True  # Reinvest profits

class SafeOrderStrategy:
    """
    Advanced DCA strategy with safety orders and grid trading
    Suitable for volatile markets and accumulation
    """
    
    def __init__(self, client, symbol: str, config: SafeOrderConfig = None):
        self.client = client
        self.symbol = symbol
        self.config = config or SafeOrderConfig()
        
        # Position tracking
        self.position = None
        self.orders = []
        self.safety_orders_placed = 0
        self.total_invested = 0.0
        self.average_price = 0.0
        
        # Performance tracking
        self.total_profit = 0.0
        self.win_count = 0
        self.loss_count = 0
        
        logger.info(f"SafeOrderStrategy initialized for {symbol}")
    
    def calculate_safety_order_levels(self, entry_price: float) -> List[Dict]:
        """Calculate safety order levels based on configuration"""
        levels = []
        current_deviation = self.config.safety_order_price_deviation
        current_volume = self.config.safety_order_size
        
        for i in range(self.config.max_safety_orders):
            # Calculate price for this safety order
            price = entry_price * (1 - current_deviation / 100)
            
            # Calculate volume for this safety order
            volume = current_volume
            
            levels.append({
                'order_num': i + 1,
                'price': price,
                'volume': volume,
                'deviation': current_deviation,
                'total_volume': self.config.base_order_size + sum(l['volume'] for l in levels) + volume
            })
            
            # Scale for next order
            current_deviation = current_deviation * self.config.safety_order_step_scale
            current_volume = current_volume * self.config.safety_order_volume_scale
        
        return levels
    
    def calculate_take_profit_price(self, average_price: float, side: str) -> float:
        """Calculate take profit price based on average entry"""
        if side == "Buy":
            return average_price * (1 + self.config.take_profit / 100)
        else:
            return average_price * (1 - self.config.take_profit / 100)
    
    def calculate_position_size(self, price: float, order_num: int = 0) -> float:
        """Calculate position size for order"""
        if order_num == 0:
            # Base order
            return self.config.base_order_size / price
        else:
            # Safety order
            volume = self.config.safety_order_size
            for _ in range(order_num - 1):
                volume *= self.config.safety_order_volume_scale
            return volume / price
    
    def should_open_position(self, market_data: Dict) -> Tuple[bool, str, float]:
        """
        Determine if we should open a new position
        Returns: (should_open, side, confidence)
        """
        price = market_data.get('price', 0)
        
        # Check if we already have a position
        if self.position:
            return False, "", 0
        
        # Simple entry logic - can be enhanced with indicators
        # For now, we'll use RSI if available
        rsi = market_data.get('rsi', 50)
        
        if rsi < 30:
            # Oversold - potential buy
            return True, "Buy", (30 - rsi) / 30
        elif rsi > 70:
            # Overbought - potential sell/short
            return True, "Sell", (rsi - 70) / 30
        
        return False, "", 0
    
    def place_base_order(self, side: str, price: float) -> Optional[str]:
        """Place the initial base order"""
        try:
            quantity = self.calculate_position_size(price, 0)
            
            logger.info(f"Placing base order: {side} {quantity:.4f} {self.symbol} at {price:.2f}")
            
            order = self.client.place_order(
                category="linear",
                symbol=self.symbol,
                side=side,
                orderType="Market",
                qty=str(quantity),
                timeInForce="IOC"
            )
            
            if order['retCode'] == 0:
                order_id = order['result']['orderId']
                
                # Update position tracking
                self.position = {
                    'side': side,
                    'entry_price': price,
                    'quantity': quantity,
                    'base_order_id': order_id
                }
                self.total_invested = self.config.base_order_size
                self.average_price = price
                
                # Place safety orders
                self.place_safety_orders(price, side)
                
                # Set take profit
                tp_price = self.calculate_take_profit_price(price, side)
                self.place_take_profit_order(side, quantity, tp_price)
                
                logger.info(f"Base order placed: {order_id}")
                return order_id
                
        except Exception as e:
            logger.error(f"Error placing base order: {e}")
        
        return None
    
    def place_safety_orders(self, entry_price: float, side: str):
        """Place all safety orders as limit orders"""
        try:
            levels = self.calculate_safety_order_levels(entry_price)
            
            for level in levels:
                quantity = level['volume'] / level['price']
                
                # For buy position, place buy limit orders below
                # For sell position, place sell limit orders above
                so_side = side
                so_price = level['price']
                
                if side == "Sell":
                    # Invert for short positions
                    so_price = entry_price * (1 + level['deviation'] / 100)
                
                logger.info(f"Placing SO#{level['order_num']}: {so_side} {quantity:.4f} at {so_price:.2f}")
                
                order = self.client.place_order(
                    category="linear",
                    symbol=self.symbol,
                    side=so_side,
                    orderType="Limit",
                    qty=str(quantity),
                    price=str(so_price),
                    timeInForce="GTC"
                )
                
                if order['retCode'] == 0:
                    self.orders.append({
                        'order_id': order['result']['orderId'],
                        'type': 'safety_order',
                        'number': level['order_num'],
                        'price': so_price,
                        'quantity': quantity,
                        'volume': level['volume']
                    })
                    
        except Exception as e:
            logger.error(f"Error placing safety orders: {e}")
    
    def place_take_profit_order(self, side: str, quantity: float, price: float):
        """Place take profit order"""
        try:
            # Opposite side for TP
            tp_side = "Sell" if side == "Buy" else "Buy"
            
            logger.info(f"Placing TP: {tp_side} {quantity:.4f} at {price:.2f}")
            
            order = self.client.place_order(
                category="linear",
                symbol=self.symbol,
                side=tp_side,
                orderType="Limit",
                qty=str(quantity),
                price=str(price),
                timeInForce="GTC",
                reduceOnly=True
            )
            
            if order['retCode'] == 0:
                self.orders.append({
                    'order_id': order['result']['orderId'],
                    'type': 'take_profit',
                    'price': price,
                    'quantity': quantity
                })
                
        except Exception as e:
            logger.error(f"Error placing take profit: {e}")
    
    def update_position(self, filled_order: Dict):
        """Update position when a safety order is filled"""
        if not self.position:
            return
        
        # Calculate new average price
        old_total = self.average_price * self.position['quantity']
        new_total = filled_order['price'] * filled_order['quantity']
        
        self.position['quantity'] += filled_order['quantity']
        self.average_price = (old_total + new_total) / self.position['quantity']
        self.total_invested += filled_order['volume']
        self.safety_orders_placed += 1
        
        # Update take profit based on new average
        new_tp_price = self.calculate_take_profit_price(
            self.average_price, 
            self.position['side']
        )
        
        # Cancel old TP and place new one
        self.update_take_profit(new_tp_price)
        
        logger.info(f"Position updated: Avg price={self.average_price:.2f}, "
                   f"Size={self.position['quantity']:.4f}, "
                   f"Invested={self.total_invested:.2f}")
    
    def update_take_profit(self, new_price: float):
        """Update take profit order with new price"""
        try:
            # Cancel existing TP order
            for order in self.orders:
                if order['type'] == 'take_profit':
                    self.client.cancel_order(
                        category="linear",
                        symbol=self.symbol,
                        orderId=order['order_id']
                    )
                    self.orders.remove(order)
                    break
            
            # Place new TP order
            if self.position:
                self.place_take_profit_order(
                    self.position['side'],
                    self.position['quantity'],
                    new_price
                )
                
        except Exception as e:
            logger.error(f"Error updating take profit: {e}")
    
    def check_orders_status(self):
        """Check status of all orders and update position"""
        try:
            for order in self.orders[:]:  # Copy list to allow modification
                result = self.client.get_open_orders(
                    category="linear",
                    symbol=self.symbol,
                    orderId=order['order_id']
                )
                
                if result['retCode'] == 0:
                    order_list = result['result']['list']
                    if not order_list:
                        # Order was filled or cancelled
                        if order['type'] == 'safety_order':
                            # Safety order filled - update position
                            self.update_position(order)
                        elif order['type'] == 'take_profit':
                            # Take profit hit - close position
                            self.close_position(profit=True)
                        
                        self.orders.remove(order)
                        
        except Exception as e:
            logger.error(f"Error checking orders: {e}")
    
    def close_position(self, profit: bool = False):
        """Close position and cancel all orders"""
        try:
            # Cancel all remaining orders
            for order in self.orders:
                self.client.cancel_order(
                    category="linear",
                    symbol=self.symbol,
                    orderId=order['order_id']
                )
            
            # Calculate profit/loss
            if self.position and profit:
                profit_amount = (self.config.take_profit / 100) * self.total_invested
                self.total_profit += profit_amount
                self.win_count += 1
                logger.info(f"Position closed with profit: ${profit_amount:.2f}")
            else:
                self.loss_count += 1
                logger.info("Position closed")
            
            # Reset position tracking
            self.position = None
            self.orders = []
            self.safety_orders_placed = 0
            self.total_invested = 0.0
            self.average_price = 0.0
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
    
    def get_statistics(self) -> Dict:
        """Get strategy statistics"""
        total_trades = self.win_count + self.loss_count
        win_rate = (self.win_count / total_trades * 100) if total_trades > 0 else 0
        
        return {
            'total_profit': self.total_profit,
            'total_trades': total_trades,
            'win_count': self.win_count,
            'loss_count': self.loss_count,
            'win_rate': win_rate,
            'current_position': self.position is not None,
            'safety_orders_used': self.safety_orders_placed,
            'average_price': self.average_price,
            'total_invested': self.total_invested
        }