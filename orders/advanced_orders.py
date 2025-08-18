"""
Advanced Order Management System
Handles Stop-Loss, Take-Profit, and Trailing Stop orders
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class OrderType(Enum):
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TRAILING_STOP = "trailing_stop"
    STOP_LIMIT = "stop_limit"
    TAKE_PROFIT_LIMIT = "take_profit_limit"

class TrailingMethod(Enum):
    PERCENTAGE = "percentage"
    ATR = "atr"
    FIXED = "fixed"
    STEP = "step"

@dataclass
class StopLossOrder:
    """Stop-Loss order configuration"""
    symbol: str
    side: str  # Buy or Sell
    quantity: float
    trigger_price: float
    order_type: str = "Market"
    time_in_force: str = "GTC"
    reduce_only: bool = True
    close_on_trigger: bool = False
    
@dataclass
class TakeProfitOrder:
    """Take-Profit order configuration"""
    symbol: str
    side: str
    quantity: float
    trigger_price: float
    limit_price: Optional[float] = None
    order_type: str = "Market"
    time_in_force: str = "GTC"
    reduce_only: bool = True

@dataclass
class TrailingStopConfig:
    """Trailing Stop configuration"""
    symbol: str
    side: str
    quantity: float
    method: TrailingMethod
    trail_value: float  # Percentage or fixed amount
    activation_price: Optional[float] = None
    step_size: Optional[float] = None  # For step trailing

class AdvancedOrderManager:
    """Manages advanced order types with dynamic adjustments"""
    
    def __init__(self, trading_client):
        """
        Initialize Advanced Order Manager
        
        Args:
            trading_client: Bybit trading client instance
        """
        self.client = trading_client
        self.active_orders = {}
        self.trailing_stops = {}
        self.order_history = []
        self.position_orders = {}  # Maps positions to their protective orders
        
    async def place_stop_loss(self, position_id: str, stop_loss: StopLossOrder) -> Dict[str, Any]:
        """
        Place a stop-loss order for a position
        
        Args:
            position_id: Position identifier
            stop_loss: Stop-loss configuration
            
        Returns:
            Order placement result
        """
        try:
            # Validate stop-loss price
            current_price = await self._get_current_price(stop_loss.symbol)
            if not self._validate_stop_loss(stop_loss, current_price):
                raise ValueError(f"Invalid stop-loss price: {stop_loss.trigger_price}")
            
            # Place conditional order
            order_params = {
                "category": "linear",
                "symbol": stop_loss.symbol,
                "side": stop_loss.side,
                "orderType": stop_loss.order_type,
                "qty": str(stop_loss.quantity),
                "triggerPrice": str(stop_loss.trigger_price),
                "triggerDirection": 1 if stop_loss.side == "Sell" else 2,  # 1: rise, 2: fall
                "timeInForce": stop_loss.time_in_force,
                "reduceOnly": stop_loss.reduce_only,
                "closeOnTrigger": stop_loss.close_on_trigger
            }
            
            result = await self.client.place_order(**order_params)
            
            if result["retCode"] == 0:
                order_id = result["result"]["orderId"]
                self.active_orders[order_id] = {
                    "type": OrderType.STOP_LOSS,
                    "position_id": position_id,
                    "config": stop_loss,
                    "status": "active",
                    "created_at": datetime.now()
                }
                
                # Link to position
                if position_id not in self.position_orders:
                    self.position_orders[position_id] = {}
                self.position_orders[position_id]["stop_loss"] = order_id
                
                logger.info(f"Stop-loss placed for position {position_id}: {order_id}")
                return result["result"]
            else:
                logger.error(f"Failed to place stop-loss: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error placing stop-loss: {e}")
            raise
    
    async def place_take_profit(self, position_id: str, take_profit: TakeProfitOrder) -> Dict[str, Any]:
        """
        Place a take-profit order for a position
        
        Args:
            position_id: Position identifier
            take_profit: Take-profit configuration
            
        Returns:
            Order placement result
        """
        try:
            # Validate take-profit price
            current_price = await self._get_current_price(take_profit.symbol)
            if not self._validate_take_profit(take_profit, current_price):
                raise ValueError(f"Invalid take-profit price: {take_profit.trigger_price}")
            
            # Place conditional order
            order_params = {
                "category": "linear",
                "symbol": take_profit.symbol,
                "side": take_profit.side,
                "orderType": take_profit.order_type,
                "qty": str(take_profit.quantity),
                "triggerPrice": str(take_profit.trigger_price),
                "triggerDirection": 2 if take_profit.side == "Sell" else 1,  # 1: rise, 2: fall
                "timeInForce": take_profit.time_in_force,
                "reduceOnly": take_profit.reduce_only
            }
            
            # Add limit price if specified
            if take_profit.limit_price:
                order_params["price"] = str(take_profit.limit_price)
                order_params["orderType"] = "Limit"
            
            result = await self.client.place_order(**order_params)
            
            if result["retCode"] == 0:
                order_id = result["result"]["orderId"]
                self.active_orders[order_id] = {
                    "type": OrderType.TAKE_PROFIT,
                    "position_id": position_id,
                    "config": take_profit,
                    "status": "active",
                    "created_at": datetime.now()
                }
                
                # Link to position
                if position_id not in self.position_orders:
                    self.position_orders[position_id] = {}
                self.position_orders[position_id]["take_profit"] = order_id
                
                logger.info(f"Take-profit placed for position {position_id}: {order_id}")
                return result["result"]
            else:
                logger.error(f"Failed to place take-profit: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error placing take-profit: {e}")
            raise
    
    async def setup_trailing_stop(self, position_id: str, config: TrailingStopConfig) -> str:
        """
        Setup a trailing stop for a position
        
        Args:
            position_id: Position identifier
            config: Trailing stop configuration
            
        Returns:
            Trailing stop ID
        """
        try:
            current_price = await self._get_current_price(config.symbol)
            
            # Initialize trailing stop
            trailing_id = f"trail_{position_id}_{datetime.now().timestamp()}"
            
            self.trailing_stops[trailing_id] = {
                "position_id": position_id,
                "config": config,
                "status": "active",
                "current_stop": self._calculate_initial_stop(config, current_price),
                "highest_price": current_price if config.side == "Sell" else None,
                "lowest_price": current_price if config.side == "Buy" else None,
                "last_update": datetime.now(),
                "created_at": datetime.now()
            }
            
            # Link to position
            if position_id not in self.position_orders:
                self.position_orders[position_id] = {}
            self.position_orders[position_id]["trailing_stop"] = trailing_id
            
            logger.info(f"Trailing stop setup for position {position_id}: {trailing_id}")
            return trailing_id
            
        except Exception as e:
            logger.error(f"Error setting up trailing stop: {e}")
            raise
    
    async def update_trailing_stops(self, market_data: Dict[str, float]):
        """
        Update all active trailing stops based on market data
        
        Args:
            market_data: Dictionary of symbol prices
        """
        for trailing_id, trailing_data in self.trailing_stops.items():
            if trailing_data["status"] != "active":
                continue
                
            config = trailing_data["config"]
            symbol = config.symbol
            
            if symbol not in market_data:
                continue
                
            current_price = market_data[symbol]
            
            # Check if activation price is met
            if config.activation_price:
                if config.side == "Sell" and current_price < config.activation_price:
                    continue
                elif config.side == "Buy" and current_price > config.activation_price:
                    continue
            
            # Update trailing stop
            new_stop = self._calculate_trailing_stop(trailing_data, current_price)
            
            if new_stop != trailing_data["current_stop"]:
                # Update the stop order
                await self._update_stop_order(trailing_id, new_stop)
                
                trailing_data["current_stop"] = new_stop
                trailing_data["last_update"] = datetime.now()
                
                # Update highest/lowest price
                if config.side == "Sell":
                    trailing_data["highest_price"] = max(
                        trailing_data["highest_price"] or current_price,
                        current_price
                    )
                else:
                    trailing_data["lowest_price"] = min(
                        trailing_data["lowest_price"] or current_price,
                        current_price
                    )
                
                logger.info(f"Trailing stop {trailing_id} updated to {new_stop}")
    
    def _calculate_initial_stop(self, config: TrailingStopConfig, current_price: float) -> float:
        """Calculate initial stop price for trailing stop"""
        if config.method == TrailingMethod.PERCENTAGE:
            if config.side == "Sell":
                return current_price * (1 - config.trail_value / 100)
            else:
                return current_price * (1 + config.trail_value / 100)
                
        elif config.method == TrailingMethod.FIXED:
            if config.side == "Sell":
                return current_price - config.trail_value
            else:
                return current_price + config.trail_value
                
        elif config.method == TrailingMethod.ATR:
            # ATR-based calculation would require ATR indicator value
            atr_value = config.trail_value  # This should be ATR * multiplier
            if config.side == "Sell":
                return current_price - atr_value
            else:
                return current_price + atr_value
                
        elif config.method == TrailingMethod.STEP:
            # Step-based trailing
            step_size = config.step_size or config.trail_value
            if config.side == "Sell":
                return current_price - step_size
            else:
                return current_price + step_size
    
    def _calculate_trailing_stop(self, trailing_data: Dict, current_price: float) -> float:
        """Calculate new trailing stop price"""
        config = trailing_data["config"]
        current_stop = trailing_data["current_stop"]
        
        if config.method == TrailingMethod.PERCENTAGE:
            if config.side == "Sell":
                # For sell positions, trail up as price rises
                new_stop = current_price * (1 - config.trail_value / 100)
                return max(current_stop, new_stop)
            else:
                # For buy positions, trail down as price falls
                new_stop = current_price * (1 + config.trail_value / 100)
                return min(current_stop, new_stop)
                
        elif config.method == TrailingMethod.FIXED:
            if config.side == "Sell":
                new_stop = current_price - config.trail_value
                return max(current_stop, new_stop)
            else:
                new_stop = current_price + config.trail_value
                return min(current_stop, new_stop)
                
        elif config.method == TrailingMethod.STEP:
            step_size = config.step_size or config.trail_value
            
            if config.side == "Sell":
                highest = trailing_data["highest_price"] or current_price
                if current_price > highest:
                    # Price moved up by at least step_size
                    steps = int((current_price - highest) / step_size)
                    if steps > 0:
                        return current_stop + (steps * step_size)
            else:
                lowest = trailing_data["lowest_price"] or current_price
                if current_price < lowest:
                    # Price moved down by at least step_size
                    steps = int((lowest - current_price) / step_size)
                    if steps > 0:
                        return current_stop - (steps * step_size)
        
        return current_stop
    
    async def _update_stop_order(self, trailing_id: str, new_stop_price: float):
        """Update the actual stop order on exchange"""
        trailing_data = self.trailing_stops[trailing_id]
        position_id = trailing_data["position_id"]
        
        # Cancel existing stop order if any
        if position_id in self.position_orders:
            if "stop_loss" in self.position_orders[position_id]:
                old_order_id = self.position_orders[position_id]["stop_loss"]
                await self.cancel_order(old_order_id)
        
        # Place new stop order
        config = trailing_data["config"]
        
        # Determine correct side for stop order (opposite of position side)
        stop_side = "Buy" if config.side == "Sell" else "Sell"
        
        stop_loss = StopLossOrder(
            symbol=config.symbol,
            side=stop_side,
            quantity=config.quantity,
            trigger_price=new_stop_price,
            reduce_only=True
        )
        
        await self.place_stop_loss(position_id, stop_loss)
    
    async def modify_order(self, order_id: str, modifications: Dict[str, Any]) -> Dict[str, Any]:
        """
        Modify an existing order
        
        Args:
            order_id: Order ID to modify
            modifications: Dictionary of fields to modify
            
        Returns:
            Modification result
        """
        try:
            if order_id not in self.active_orders:
                raise ValueError(f"Order {order_id} not found")
            
            order_data = self.active_orders[order_id]
            
            # Build modification parameters
            modify_params = {
                "category": "linear",
                "symbol": order_data["config"].symbol,
                "orderId": order_id
            }
            
            # Add modifications
            if "trigger_price" in modifications:
                modify_params["triggerPrice"] = str(modifications["trigger_price"])
            if "quantity" in modifications:
                modify_params["qty"] = str(modifications["quantity"])
            if "limit_price" in modifications:
                modify_params["price"] = str(modifications["limit_price"])
            
            result = await self.client.amend_order(**modify_params)
            
            if result["retCode"] == 0:
                # Update local order data
                for key, value in modifications.items():
                    setattr(order_data["config"], key, value)
                
                logger.info(f"Order {order_id} modified successfully")
                return result["result"]
            else:
                logger.error(f"Failed to modify order: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error modifying order: {e}")
            raise
    
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Success status
        """
        try:
            if order_id not in self.active_orders:
                logger.warning(f"Order {order_id} not in active orders")
                return False
            
            order_data = self.active_orders[order_id]
            
            result = await self.client.cancel_order(
                category="linear",
                symbol=order_data["config"].symbol,
                orderId=order_id
            )
            
            if result["retCode"] == 0:
                # Update order status
                order_data["status"] = "cancelled"
                order_data["cancelled_at"] = datetime.now()
                
                # Move to history
                self.order_history.append(order_data)
                del self.active_orders[order_id]
                
                # Remove from position orders
                position_id = order_data["position_id"]
                if position_id in self.position_orders:
                    for order_type in ["stop_loss", "take_profit"]:
                        if self.position_orders[position_id].get(order_type) == order_id:
                            del self.position_orders[position_id][order_type]
                
                logger.info(f"Order {order_id} cancelled")
                return True
            else:
                logger.error(f"Failed to cancel order: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
    
    async def cancel_position_orders(self, position_id: str) -> int:
        """
        Cancel all orders associated with a position
        
        Args:
            position_id: Position identifier
            
        Returns:
            Number of orders cancelled
        """
        cancelled_count = 0
        
        if position_id in self.position_orders:
            # Create a copy of items to avoid dictionary changed size error
            position_orders_copy = dict(self.position_orders[position_id].items())
            
            for order_type, order_id in position_orders_copy.items():
                if order_type == "trailing_stop":
                    # Deactivate trailing stop
                    if order_id in self.trailing_stops:
                        self.trailing_stops[order_id]["status"] = "cancelled"
                        cancelled_count += 1
                else:
                    # Cancel regular order
                    if await self.cancel_order(order_id):
                        cancelled_count += 1
            
            del self.position_orders[position_id]
        
        return cancelled_count
    
    def handle_partial_fill(self, order_id: str, filled_qty: float, remaining_qty: float):
        """
        Handle partial order fills
        
        Args:
            order_id: Order ID
            filled_qty: Quantity filled
            remaining_qty: Quantity remaining
        """
        if order_id in self.active_orders:
            order_data = self.active_orders[order_id]
            
            # Update order quantities
            order_data["filled_qty"] = filled_qty
            order_data["remaining_qty"] = remaining_qty
            order_data["last_fill_time"] = datetime.now()
            
            # Calculate fill percentage
            total_qty = order_data["config"].quantity
            fill_percentage = (filled_qty / total_qty) * 100
            
            logger.info(f"Order {order_id} partially filled: {fill_percentage:.2f}%")
            
            # If order is protective (SL/TP), may need to adjust
            if fill_percentage > 90:  # Nearly filled
                logger.warning(f"Order {order_id} nearly filled, consider adjusting")
    
    def calculate_break_even_stop(self, entry_price: float, commission_rate: float = 0.0006) -> float:
        """
        Calculate break-even stop loss price including fees
        
        Args:
            entry_price: Position entry price
            commission_rate: Trading commission rate
            
        Returns:
            Break-even price
        """
        # Account for entry and exit commissions
        total_commission = commission_rate * 2
        break_even = entry_price * (1 + total_commission)
        
        return round(break_even, 2)
    
    def calculate_risk_based_stop(self, entry_price: float, position_size: float, 
                                  max_loss: float, side: str) -> float:
        """
        Calculate stop loss based on maximum acceptable loss
        
        Args:
            entry_price: Position entry price
            position_size: Position size
            max_loss: Maximum acceptable loss amount
            side: Position side (Buy/Sell)
            
        Returns:
            Stop loss price
        """
        max_loss_per_unit = max_loss / position_size
        
        if side == "Buy":
            stop_price = entry_price - max_loss_per_unit
        else:
            stop_price = entry_price + max_loss_per_unit
        
        return round(stop_price, 2)
    
    def calculate_atr_based_stop(self, entry_price: float, atr: float, 
                                 multiplier: float, side: str) -> float:
        """
        Calculate stop loss based on ATR
        
        Args:
            entry_price: Position entry price
            atr: Average True Range value
            multiplier: ATR multiplier (typically 1.5-3)
            side: Position side
            
        Returns:
            Stop loss price
        """
        stop_distance = atr * multiplier
        
        if side == "Buy":
            stop_price = entry_price - stop_distance
        else:
            stop_price = entry_price + stop_distance
        
        return round(stop_price, 2)
    
    def _validate_stop_loss(self, stop_loss: StopLossOrder, current_price: float) -> bool:
        """Validate stop-loss price is logical"""
        if stop_loss.side == "Sell":  # Closing a long position
            return stop_loss.trigger_price < current_price
        else:  # Closing a short position
            return stop_loss.trigger_price > current_price
    
    def _validate_take_profit(self, take_profit: TakeProfitOrder, current_price: float) -> bool:
        """Validate take-profit price is logical"""
        if take_profit.side == "Sell":  # Closing a long position
            return take_profit.trigger_price > current_price
        else:  # Closing a short position
            return take_profit.trigger_price < current_price
    
    async def _get_current_price(self, symbol: str) -> float:
        """Get current market price for symbol"""
        try:
            ticker = await self.client.get_tickers(category="linear", symbol=symbol)
            if ticker["retCode"] == 0 and ticker["result"]["list"]:
                return float(ticker["result"]["list"][0]["lastPrice"])
            return 0.0
        except Exception as e:
            logger.error(f"Error getting current price: {e}")
            return 0.0
    
    def get_position_orders(self, position_id: str) -> Dict[str, Any]:
        """Get all orders associated with a position"""
        if position_id in self.position_orders:
            orders = {}
            for order_type, order_id in self.position_orders[position_id].items():
                if order_type == "trailing_stop":
                    if order_id in self.trailing_stops:
                        orders[order_type] = self.trailing_stops[order_id]
                else:
                    if order_id in self.active_orders:
                        orders[order_type] = self.active_orders[order_id]
            return orders
        return {}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get order management statistics"""
        return {
            "active_orders": len(self.active_orders),
            "active_trailing_stops": len([t for t in self.trailing_stops.values() 
                                         if t["status"] == "active"]),
            "protected_positions": len(self.position_orders),
            "order_history": len(self.order_history),
            "order_types": {
                "stop_loss": len([o for o in self.active_orders.values() 
                                 if o["type"] == OrderType.STOP_LOSS]),
                "take_profit": len([o for o in self.active_orders.values() 
                                   if o["type"] == OrderType.TAKE_PROFIT]),
                "trailing_stop": len([t for t in self.trailing_stops.values() 
                                     if t["status"] == "active"])
            }
        }