"""
Order Management System for Bybit Trading Bot
Handles order lifecycle, execution, and tracking
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass, field, asdict
import uuid
import threading
from collections import deque
import json

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order types"""
    MARKET = "Market"
    LIMIT = "Limit"
    STOP = "Stop"
    STOP_LIMIT = "StopLimit"
    TAKE_PROFIT = "TakeProfit"
    TAKE_PROFIT_LIMIT = "TakeProfitLimit"


class OrderSide(Enum):
    """Order sides"""
    BUY = "Buy"
    SELL = "Sell"


class OrderStatus(Enum):
    """Order status"""
    PENDING = "Pending"
    NEW = "New"
    PARTIALLY_FILLED = "PartiallyFilled"
    FILLED = "Filled"
    CANCELLED = "Cancelled"
    REJECTED = "Rejected"
    EXPIRED = "Expired"


class TimeInForce(Enum):
    """Time in force types"""
    GTC = "GTC"  # Good Till Cancelled
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill
    POST_ONLY = "PostOnly"


@dataclass
class Order:
    """Order data structure"""
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    client_order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.LIMIT
    quantity: float = 0.0
    price: float = 0.0
    stop_price: float = 0.0
    time_in_force: TimeInForce = TimeInForce.GTC
    reduce_only: bool = False
    close_on_trigger: bool = False
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    remaining_quantity: float = 0.0
    average_fill_price: float = 0.0
    last_fill_price: float = 0.0
    last_fill_quantity: float = 0.0
    commission: float = 0.0
    commission_asset: str = "USDT"
    created_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    filled_time: Optional[datetime] = None
    exchange_order_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        self.remaining_quantity = self.quantity - self.filled_quantity
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data["side"] = self.side.value
        data["order_type"] = self.order_type.value
        data["status"] = self.status.value
        data["time_in_force"] = self.time_in_force.value
        data["created_time"] = self.created_time.isoformat()
        data["updated_time"] = self.updated_time.isoformat()
        data["filled_time"] = self.filled_time.isoformat() if self.filled_time else None
        return data


@dataclass
class OrderUpdate:
    """Order update/fill information"""
    order_id: str
    update_type: str  # "fill", "status", "cancel"
    timestamp: datetime
    fill_price: float = 0.0
    fill_quantity: float = 0.0
    commission: float = 0.0
    new_status: Optional[OrderStatus] = None
    message: str = ""


class OrderManager:
    """Manages order lifecycle, execution, and tracking"""
    
    def __init__(self, bybit_client=None, risk_manager=None):
        self.client = bybit_client
        self.risk_manager = risk_manager
        self.orders = {}  # order_id -> Order
        self.active_orders = {}  # symbol -> List[Order]
        self.order_history = deque(maxlen=1000)
        self.fills = deque(maxlen=5000)
        self.order_lock = threading.Lock()
        
        # Order routing configuration
        self.routing_rules = {
            "max_order_size": {},  # symbol -> max size
            "min_order_size": {},  # symbol -> min size
            "tick_size": {},  # symbol -> tick size
            "lot_size": {},  # symbol -> lot size
        }
        
        # Performance metrics
        self.metrics = {
            "total_orders": 0,
            "filled_orders": 0,
            "cancelled_orders": 0,
            "rejected_orders": 0,
            "total_volume": 0.0,
            "total_commission": 0.0,
            "average_fill_time": 0.0,
            "fill_rate": 0.0
        }
        
        # Smart order routing settings
        self.smart_routing = {
            "enabled": True,
            "split_large_orders": True,
            "max_slippage": 0.002,  # 0.2%
            "use_iceberg": True,
            "iceberg_percent": 0.1  # Show 10% of total order
        }
        
        logger.info("Order Manager initialized")
    
    def create_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: float = 0.0,
        stop_price: float = 0.0,
        time_in_force: TimeInForce = TimeInForce.GTC,
        reduce_only: bool = False,
        metadata: Dict[str, Any] = None
    ) -> Order:
        """Create a new order"""
        try:
            # Create order object
            order = Order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                stop_price=stop_price,
                time_in_force=time_in_force,
                reduce_only=reduce_only,
                metadata=metadata or {}
            )
            
            # Validate order
            validation_result = self.validate_order(order)
            if not validation_result["valid"]:
                order.status = OrderStatus.REJECTED
                logger.error(f"Order validation failed: {validation_result['reason']}")
                return order
            
            # Risk check
            if self.risk_manager:
                risk_check = self.risk_manager.check_order_risk(order.to_dict())
                if not risk_check["approved"]:
                    order.status = OrderStatus.REJECTED
                    order.metadata["rejection_reason"] = risk_check.get("reason", "Risk check failed")
                    logger.warning(f"Order rejected by risk manager: {risk_check.get('reason')}")
                    return order
            
            # Apply smart routing if enabled
            if self.smart_routing["enabled"]:
                order = self._apply_smart_routing(order)
            
            # Store order
            with self.order_lock:
                self.orders[order.order_id] = order
                if symbol not in self.active_orders:
                    self.active_orders[symbol] = []
                self.active_orders[symbol].append(order)
                self.metrics["total_orders"] += 1
            
            logger.info(f"Order created: {order.order_id} - {symbol} {side.value} {quantity} @ {price}")
            return order
            
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return Order(status=OrderStatus.REJECTED)
    
    def submit_order(self, order: Order) -> bool:
        """Submit order to exchange"""
        try:
            if not self.client:
                logger.error("Bybit client not initialized")
                return False
            
            if order.status != OrderStatus.PENDING:
                logger.error(f"Cannot submit order in status: {order.status}")
                return False
            
            # Prepare order parameters
            params = {
                "category": "spot",  # or "linear", "inverse"
                "symbol": order.symbol,
                "side": order.side.value,
                "orderType": order.order_type.value,
                "qty": str(order.quantity),
                "timeInForce": order.time_in_force.value,
                "orderLinkId": order.client_order_id
            }
            
            # Add price for limit orders
            if order.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT, OrderType.TAKE_PROFIT_LIMIT]:
                params["price"] = str(order.price)
            
            # Add stop price for stop orders
            if order.order_type in [OrderType.STOP, OrderType.STOP_LIMIT]:
                params["triggerPrice"] = str(order.stop_price)
            
            # Add reduce only flag
            if order.reduce_only:
                params["reduceOnly"] = True
            
            # Submit order to exchange
            response = self.client.session.place_order(**params)
            
            if response["retCode"] == 0:
                # Update order with exchange response
                order.exchange_order_id = response["result"]["orderId"]
                order.status = OrderStatus.NEW
                order.updated_time = datetime.now(timezone.utc)
                
                logger.info(f"Order submitted successfully: {order.order_id} -> {order.exchange_order_id}")
                return True
            else:
                # Order rejected by exchange
                order.status = OrderStatus.REJECTED
                order.metadata["rejection_reason"] = response.get("retMsg", "Unknown error")
                self.metrics["rejected_orders"] += 1
                
                logger.error(f"Order rejected by exchange: {response.get('retMsg')}")
                return False
                
        except Exception as e:
            logger.error(f"Error submitting order: {e}")
            order.status = OrderStatus.REJECTED
            order.metadata["rejection_reason"] = str(e)
            return False
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        try:
            order = self.orders.get(order_id)
            if not order:
                logger.error(f"Order not found: {order_id}")
                return False
            
            if order.status not in [OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED]:
                logger.error(f"Cannot cancel order in status: {order.status}")
                return False
            
            if self.client and order.exchange_order_id:
                # Cancel on exchange
                response = self.client.session.cancel_order(
                    category="spot",
                    symbol=order.symbol,
                    orderId=order.exchange_order_id
                )
                
                if response["retCode"] == 0:
                    order.status = OrderStatus.CANCELLED
                    order.updated_time = datetime.now(timezone.utc)
                    self.metrics["cancelled_orders"] += 1
                    
                    # Remove from active orders
                    with self.order_lock:
                        if order.symbol in self.active_orders:
                            self.active_orders[order.symbol] = [
                                o for o in self.active_orders[order.symbol]
                                if o.order_id != order_id
                            ]
                    
                    logger.info(f"Order cancelled: {order_id}")
                    return True
                else:
                    logger.error(f"Failed to cancel order: {response.get('retMsg')}")
                    return False
            else:
                # Local cancellation
                order.status = OrderStatus.CANCELLED
                order.updated_time = datetime.now(timezone.utc)
                return True
                
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
    
    def modify_order(
        self,
        order_id: str,
        new_quantity: Optional[float] = None,
        new_price: Optional[float] = None
    ) -> bool:
        """Modify an existing order"""
        try:
            order = self.orders.get(order_id)
            if not order:
                logger.error(f"Order not found: {order_id}")
                return False
            
            if order.status != OrderStatus.NEW:
                logger.error(f"Cannot modify order in status: {order.status}")
                return False
            
            if self.client and order.exchange_order_id:
                # Prepare modification parameters
                params = {
                    "category": "spot",
                    "symbol": order.symbol,
                    "orderId": order.exchange_order_id
                }
                
                if new_quantity is not None:
                    params["qty"] = str(new_quantity)
                    order.quantity = new_quantity
                    order.remaining_quantity = new_quantity - order.filled_quantity
                
                if new_price is not None:
                    params["price"] = str(new_price)
                    order.price = new_price
                
                # Modify on exchange
                response = self.client.session.amend_order(**params)
                
                if response["retCode"] == 0:
                    order.updated_time = datetime.now(timezone.utc)
                    logger.info(f"Order modified: {order_id}")
                    return True
                else:
                    logger.error(f"Failed to modify order: {response.get('retMsg')}")
                    return False
            else:
                # Local modification
                if new_quantity is not None:
                    order.quantity = new_quantity
                    order.remaining_quantity = new_quantity - order.filled_quantity
                if new_price is not None:
                    order.price = new_price
                order.updated_time = datetime.now(timezone.utc)
                return True
                
        except Exception as e:
            logger.error(f"Error modifying order: {e}")
            return False
    
    def process_fill(self, order_id: str, fill: Dict[str, Any]):
        """Process order fill/execution"""
        try:
            order = self.orders.get(order_id)
            if not order:
                logger.error(f"Order not found for fill: {order_id}")
                return
            
            # Update order with fill information
            fill_quantity = float(fill.get("qty", 0))
            fill_price = float(fill.get("price", 0))
            commission = float(fill.get("commission", 0))
            
            order.filled_quantity += fill_quantity
            order.remaining_quantity = order.quantity - order.filled_quantity
            order.last_fill_price = fill_price
            order.last_fill_quantity = fill_quantity
            order.commission += commission
            
            # Update average fill price
            if order.filled_quantity > 0:
                if order.average_fill_price == 0:
                    order.average_fill_price = fill_price
                else:
                    # Weighted average
                    total_value = (order.average_fill_price * (order.filled_quantity - fill_quantity) +
                                 fill_price * fill_quantity)
                    order.average_fill_price = total_value / order.filled_quantity
            
            # Update status
            if order.filled_quantity >= order.quantity:
                order.status = OrderStatus.FILLED
                order.filled_time = datetime.now(timezone.utc)
                self.metrics["filled_orders"] += 1
                
                # Remove from active orders
                with self.order_lock:
                    if order.symbol in self.active_orders:
                        self.active_orders[order.symbol] = [
                            o for o in self.active_orders[order.symbol]
                            if o.order_id != order_id
                        ]
                    # Add to history
                    self.order_history.append(order)
            elif order.filled_quantity > 0:
                order.status = OrderStatus.PARTIALLY_FILLED
            
            order.updated_time = datetime.now(timezone.utc)
            
            # Store fill record
            fill_record = OrderUpdate(
                order_id=order_id,
                update_type="fill",
                timestamp=datetime.now(timezone.utc),
                fill_price=fill_price,
                fill_quantity=fill_quantity,
                commission=commission
            )
            self.fills.append(fill_record)
            
            # Update metrics
            self.metrics["total_volume"] += fill_quantity * fill_price
            self.metrics["total_commission"] += commission
            
            logger.info(f"Order fill processed: {order_id} - {fill_quantity} @ {fill_price}")
            
        except Exception as e:
            logger.error(f"Error processing fill: {e}")
    
    def validate_order(self, order: Order) -> Dict[str, Any]:
        """Validate order parameters"""
        try:
            # Check required fields
            if not order.symbol:
                return {"valid": False, "reason": "Symbol is required"}
            
            if order.quantity <= 0:
                return {"valid": False, "reason": "Quantity must be positive"}
            
            # Check price for limit orders
            if order.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT, OrderType.TAKE_PROFIT_LIMIT]:
                if order.price <= 0:
                    return {"valid": False, "reason": "Price must be positive for limit orders"}
            
            # Check stop price for stop orders
            if order.order_type in [OrderType.STOP, OrderType.STOP_LIMIT]:
                if order.stop_price <= 0:
                    return {"valid": False, "reason": "Stop price must be positive for stop orders"}
            
            # Check against routing rules
            if order.symbol in self.routing_rules["min_order_size"]:
                min_size = self.routing_rules["min_order_size"][order.symbol]
                if order.quantity < min_size:
                    return {"valid": False, "reason": f"Quantity below minimum: {min_size}"}
            
            if order.symbol in self.routing_rules["max_order_size"]:
                max_size = self.routing_rules["max_order_size"][order.symbol]
                if order.quantity > max_size:
                    return {"valid": False, "reason": f"Quantity above maximum: {max_size}"}
            
            # Check tick size
            if order.symbol in self.routing_rules["tick_size"] and order.price > 0:
                tick_size = self.routing_rules["tick_size"][order.symbol]
                if order.price % tick_size != 0:
                    # Round to nearest tick
                    order.price = round(order.price / tick_size) * tick_size
            
            # Check lot size
            if order.symbol in self.routing_rules["lot_size"]:
                lot_size = self.routing_rules["lot_size"][order.symbol]
                if order.quantity % lot_size != 0:
                    # Round to nearest lot
                    order.quantity = round(order.quantity / lot_size) * lot_size
            
            return {"valid": True, "reason": "Order validated successfully"}
            
        except Exception as e:
            logger.error(f"Error validating order: {e}")
            return {"valid": False, "reason": str(e)}
    
    def _apply_smart_routing(self, order: Order) -> Order:
        """Apply smart order routing logic"""
        try:
            # Split large orders if enabled
            if self.smart_routing["split_large_orders"]:
                max_size = self.routing_rules["max_order_size"].get(order.symbol, float('inf'))
                if order.quantity > max_size * 0.5:  # If order is > 50% of max size
                    # Create iceberg order
                    if self.smart_routing["use_iceberg"]:
                        visible_quantity = order.quantity * self.smart_routing["iceberg_percent"]
                        order.metadata["iceberg"] = True
                        order.metadata["visible_quantity"] = visible_quantity
                        order.metadata["total_quantity"] = order.quantity
                        logger.info(f"Applied iceberg routing: visible={visible_quantity}, total={order.quantity}")
            
            # Adjust price for market impact
            if order.order_type == OrderType.LIMIT:
                if order.side == OrderSide.BUY:
                    # For buy orders, slightly increase price to improve fill probability
                    order.price *= (1 + self.smart_routing["max_slippage"] * 0.1)
                else:
                    # For sell orders, slightly decrease price
                    order.price *= (1 - self.smart_routing["max_slippage"] * 0.1)
            
            # Set time in force based on order type
            if order.order_type == OrderType.MARKET:
                order.time_in_force = TimeInForce.IOC
            elif order.metadata.get("post_only", False):
                order.time_in_force = TimeInForce.POST_ONLY
            
            return order
            
        except Exception as e:
            logger.error(f"Error applying smart routing: {e}")
            return order
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_active_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get active orders"""
        if symbol:
            return self.active_orders.get(symbol, [])
        else:
            all_active = []
            for orders in self.active_orders.values():
                all_active.extend(orders)
            return all_active
    
    def get_order_history(self, limit: int = 100) -> List[Order]:
        """Get order history"""
        history = list(self.order_history)
        return history[-limit:] if len(history) > limit else history
    
    def get_fills(self, order_id: Optional[str] = None, limit: int = 100) -> List[OrderUpdate]:
        """Get fill history"""
        fills = list(self.fills)
        if order_id:
            fills = [f for f in fills if f.order_id == order_id]
        return fills[-limit:] if len(fills) > limit else fills
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        # Calculate fill rate
        if self.metrics["total_orders"] > 0:
            self.metrics["fill_rate"] = self.metrics["filled_orders"] / self.metrics["total_orders"]
        
        # Calculate average fill time
        filled_orders = [o for o in self.order_history if o.status == OrderStatus.FILLED]
        if filled_orders:
            fill_times = [
                (o.filled_time - o.created_time).total_seconds()
                for o in filled_orders
                if o.filled_time
            ]
            if fill_times:
                self.metrics["average_fill_time"] = sum(fill_times) / len(fill_times)
        
        return self.metrics
    
    def update_routing_rules(self, symbol: str, rules: Dict[str, Any]):
        """Update routing rules for a symbol"""
        if "min_order_size" in rules:
            self.routing_rules["min_order_size"][symbol] = rules["min_order_size"]
        if "max_order_size" in rules:
            self.routing_rules["max_order_size"][symbol] = rules["max_order_size"]
        if "tick_size" in rules:
            self.routing_rules["tick_size"][symbol] = rules["tick_size"]
        if "lot_size" in rules:
            self.routing_rules["lot_size"][symbol] = rules["lot_size"]
        
        logger.info(f"Updated routing rules for {symbol}")
    
    def cleanup_expired_orders(self, max_age_hours: int = 24):
        """Clean up old expired/cancelled orders"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            
            with self.order_lock:
                # Remove old orders from history
                self.order_history = deque(
                    [o for o in self.order_history if o.updated_time > cutoff_time],
                    maxlen=1000
                )
                
                # Remove old inactive orders
                for order_id, order in list(self.orders.items()):
                    if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
                        if order.updated_time < cutoff_time:
                            del self.orders[order_id]
            
            logger.info("Cleaned up expired orders")
            
        except Exception as e:
            logger.error(f"Error cleaning up orders: {e}")