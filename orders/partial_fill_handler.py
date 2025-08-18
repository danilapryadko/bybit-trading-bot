"""
Partial Fill Handler
Manages partial order fills and executes appropriate strategies
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)

class FillStrategy(Enum):
    WAIT = "wait"  # Wait for complete fill
    CANCEL_REMAINDER = "cancel_remainder"  # Cancel unfilled portion
    MODIFY_PRICE = "modify_price"  # Adjust price to fill faster
    SPLIT_ORDER = "split_order"  # Split into smaller orders
    MARKET_FILL = "market_fill"  # Convert remainder to market order

@dataclass
class PartialFill:
    """Partial fill information"""
    order_id: str
    symbol: str
    side: str
    original_qty: float
    filled_qty: float
    remaining_qty: float
    avg_fill_price: float
    last_fill_time: datetime
    fill_percentage: float
    fees_paid: float

@dataclass
class FillHandlingConfig:
    """Configuration for handling partial fills"""
    min_fill_percentage: float = 90.0  # Cancel if >90% filled
    max_wait_time: timedelta = timedelta(minutes=5)  # Max wait before action
    price_adjustment_step: float = 0.001  # 0.1% price adjustment
    split_threshold: float = 100  # Split if remaining > threshold
    auto_market_threshold: float = 10  # Convert to market if remaining < threshold

class PartialFillHandler:
    """Handles partial order fills with various strategies"""
    
    def __init__(self, trading_client, order_modifier, config: FillHandlingConfig = None):
        """
        Initialize Partial Fill Handler
        
        Args:
            trading_client: Bybit trading client
            order_modifier: Order modification system
            config: Fill handling configuration
        """
        self.client = trading_client
        self.modifier = order_modifier
        self.config = config or FillHandlingConfig()
        
        self.partial_fills = {}  # Active partial fills
        self.fill_history = []  # Historical fills
        self.monitoring = False
        self.strategies = {}  # Order ID to strategy mapping
        
    async def start_monitoring(self):
        """Start monitoring partial fills"""
        if not self.monitoring:
            self.monitoring = True
            asyncio.create_task(self._monitor_fills())
            logger.info("Partial fill monitoring started")
    
    async def stop_monitoring(self):
        """Stop monitoring partial fills"""
        self.monitoring = False
        logger.info("Partial fill monitoring stopped")
    
    async def _monitor_fills(self):
        """Monitor and handle partial fills"""
        while self.monitoring:
            try:
                # Check all partial fills
                for order_id, fill in list(self.partial_fills.items()):
                    await self._check_and_handle_fill(order_id, fill)
                
                # Wait before next check
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring fills: {e}")
    
    async def handle_fill_update(self, order_id: str, fill_data: Dict[str, Any]):
        """
        Handle a fill update from exchange
        
        Args:
            order_id: Order ID
            fill_data: Fill update data
        """
        try:
            # Parse fill data
            partial_fill = PartialFill(
                order_id=order_id,
                symbol=fill_data["symbol"],
                side=fill_data["side"],
                original_qty=float(fill_data.get("qty", 0)),
                filled_qty=float(fill_data.get("cumExecQty", 0)),
                remaining_qty=float(fill_data.get("leavesQty", 0)),
                avg_fill_price=float(fill_data.get("avgPrice", 0)),
                last_fill_time=datetime.now(),
                fill_percentage=(float(fill_data.get("cumExecQty", 0)) / 
                               float(fill_data.get("qty", 1))) * 100,
                fees_paid=float(fill_data.get("cumExecFee", 0))
            )
            
            # Check if order is completely filled
            if partial_fill.fill_percentage >= 100:
                await self._handle_complete_fill(partial_fill)
            else:
                # Add to monitoring
                self.partial_fills[order_id] = partial_fill
                
                # Determine and apply strategy
                strategy = await self._determine_strategy(partial_fill)
                await self._apply_strategy(partial_fill, strategy)
            
        except Exception as e:
            logger.error(f"Error handling fill update: {e}")
    
    async def _determine_strategy(self, fill: PartialFill) -> FillStrategy:
        """
        Determine best strategy for handling partial fill
        
        Args:
            fill: Partial fill information
            
        Returns:
            Recommended strategy
        """
        # Check if mostly filled
        if fill.fill_percentage >= self.config.min_fill_percentage:
            return FillStrategy.CANCEL_REMAINDER
        
        # Check wait time
        wait_time = datetime.now() - fill.last_fill_time
        if wait_time > self.config.max_wait_time:
            # Waited too long, take action
            if fill.remaining_qty < self.config.auto_market_threshold:
                return FillStrategy.MARKET_FILL
            elif fill.remaining_qty > self.config.split_threshold:
                return FillStrategy.SPLIT_ORDER
            else:
                return FillStrategy.MODIFY_PRICE
        
        # Default: wait for more fills
        return FillStrategy.WAIT
    
    async def _apply_strategy(self, fill: PartialFill, strategy: FillStrategy):
        """
        Apply fill handling strategy
        
        Args:
            fill: Partial fill information
            strategy: Strategy to apply
        """
        try:
            self.strategies[fill.order_id] = strategy
            
            if strategy == FillStrategy.WAIT:
                logger.info(f"Waiting for complete fill: {fill.order_id} "
                          f"({fill.fill_percentage:.1f}% filled)")
                
            elif strategy == FillStrategy.CANCEL_REMAINDER:
                await self._cancel_remainder(fill)
                
            elif strategy == FillStrategy.MODIFY_PRICE:
                await self._modify_price_for_fill(fill)
                
            elif strategy == FillStrategy.SPLIT_ORDER:
                await self._split_order(fill)
                
            elif strategy == FillStrategy.MARKET_FILL:
                await self._convert_to_market(fill)
            
        except Exception as e:
            logger.error(f"Error applying strategy {strategy}: {e}")
    
    async def _cancel_remainder(self, fill: PartialFill):
        """Cancel remaining unfilled portion"""
        try:
            result = await self.client.cancel_order(
                category="linear",
                symbol=fill.symbol,
                orderId=fill.order_id
            )
            
            if result["retCode"] == 0:
                logger.info(f"Cancelled remainder for {fill.order_id} "
                          f"({fill.remaining_qty} unfilled)")
                
                # Move to history
                self._move_to_history(fill)
            else:
                logger.error(f"Failed to cancel remainder: {result}")
                
        except Exception as e:
            logger.error(f"Error cancelling remainder: {e}")
    
    async def _modify_price_for_fill(self, fill: PartialFill):
        """Modify order price to increase fill probability"""
        try:
            # Get current market price
            ticker = await self.client.get_tickers(
                category="linear",
                symbol=fill.symbol
            )
            
            if ticker["retCode"] == 0 and ticker["result"]["list"]:
                market_price = float(ticker["result"]["list"][0]["lastPrice"])
                
                # Calculate new price
                if fill.side == "Buy":
                    # Increase buy price slightly
                    new_price = market_price * (1 + self.config.price_adjustment_step)
                else:
                    # Decrease sell price slightly
                    new_price = market_price * (1 - self.config.price_adjustment_step)
                
                # Modify order
                result = await self.modifier.modify_price(
                    fill.order_id,
                    new_price,
                    f"Partial fill adjustment ({fill.fill_percentage:.1f}% filled)"
                )
                
                if result.get("success"):
                    logger.info(f"Adjusted price for {fill.order_id} to {new_price}")
            
        except Exception as e:
            logger.error(f"Error modifying price: {e}")
    
    async def _split_order(self, fill: PartialFill):
        """Split remaining order into smaller chunks"""
        try:
            # Cancel original order
            cancel_result = await self.client.cancel_order(
                category="linear",
                symbol=fill.symbol,
                orderId=fill.order_id
            )
            
            if cancel_result["retCode"] != 0:
                logger.error(f"Failed to cancel for split: {cancel_result}")
                return
            
            # Calculate split sizes
            num_splits = 3  # Split into 3 orders
            split_size = fill.remaining_qty / num_splits
            
            # Place split orders
            for i in range(num_splits):
                order_params = {
                    "category": "linear",
                    "symbol": fill.symbol,
                    "side": fill.side,
                    "orderType": "Limit",
                    "qty": str(split_size),
                    "price": str(fill.avg_fill_price),  # Use same price
                    "timeInForce": "GTC"
                }
                
                result = await self.client.place_order(**order_params)
                
                if result["retCode"] == 0:
                    logger.info(f"Split order {i+1}/{num_splits} placed: "
                              f"{result['result']['orderId']}")
            
            # Move original to history
            self._move_to_history(fill)
            
        except Exception as e:
            logger.error(f"Error splitting order: {e}")
    
    async def _convert_to_market(self, fill: PartialFill):
        """Convert remainder to market order"""
        try:
            # Cancel original order
            cancel_result = await self.client.cancel_order(
                category="linear",
                symbol=fill.symbol,
                orderId=fill.order_id
            )
            
            if cancel_result["retCode"] != 0:
                logger.error(f"Failed to cancel for market conversion: {cancel_result}")
                return
            
            # Place market order for remainder
            market_params = {
                "category": "linear",
                "symbol": fill.symbol,
                "side": fill.side,
                "orderType": "Market",
                "qty": str(fill.remaining_qty),
                "timeInForce": "IOC"  # Immediate or cancel
            }
            
            result = await self.client.place_order(**market_params)
            
            if result["retCode"] == 0:
                logger.info(f"Market order placed for remainder: "
                          f"{result['result']['orderId']}")
            
            # Move to history
            self._move_to_history(fill)
            
        except Exception as e:
            logger.error(f"Error converting to market: {e}")
    
    async def _check_and_handle_fill(self, order_id: str, fill: PartialFill):
        """Check and handle a partial fill based on time and conditions"""
        try:
            # Update fill status
            order_status = await self._get_order_status(order_id)
            
            if not order_status:
                # Order no longer exists
                self._move_to_history(fill)
                return
            
            # Update fill data
            fill.filled_qty = float(order_status.get("cumExecQty", 0))
            fill.remaining_qty = float(order_status.get("leavesQty", 0))
            fill.fill_percentage = (fill.filled_qty / fill.original_qty) * 100
            
            # Re-evaluate strategy
            new_strategy = await self._determine_strategy(fill)
            current_strategy = self.strategies.get(order_id, FillStrategy.WAIT)
            
            # Apply new strategy if changed
            if new_strategy != current_strategy:
                logger.info(f"Strategy change for {order_id}: "
                          f"{current_strategy} -> {new_strategy}")
                await self._apply_strategy(fill, new_strategy)
            
        except Exception as e:
            logger.error(f"Error checking fill: {e}")
    
    async def _get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get current order status"""
        try:
            result = await self.client.get_open_orders(
                category="linear",
                orderId=order_id
            )
            
            if result["retCode"] == 0 and result["result"]["list"]:
                return result["result"]["list"][0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return None
    
    async def _handle_complete_fill(self, fill: PartialFill):
        """Handle completely filled order"""
        logger.info(f"Order {fill.order_id} completely filled: "
                   f"{fill.filled_qty} @ {fill.avg_fill_price}")
        
        # Remove from monitoring
        if fill.order_id in self.partial_fills:
            del self.partial_fills[fill.order_id]
        
        # Add to history
        self.fill_history.append({
            "fill": fill,
            "completed_at": datetime.now(),
            "strategy": self.strategies.get(fill.order_id, FillStrategy.WAIT)
        })
    
    def _move_to_history(self, fill: PartialFill):
        """Move partial fill to history"""
        if fill.order_id in self.partial_fills:
            del self.partial_fills[fill.order_id]
        
        self.fill_history.append({
            "fill": fill,
            "moved_at": datetime.now(),
            "strategy": self.strategies.get(fill.order_id),
            "final_status": "partial"
        })
    
    def calculate_fill_metrics(self, fill: PartialFill) -> Dict[str, Any]:
        """Calculate metrics for a partial fill"""
        return {
            "order_id": fill.order_id,
            "fill_percentage": round(fill.fill_percentage, 2),
            "filled_value": fill.filled_qty * fill.avg_fill_price,
            "remaining_value": fill.remaining_qty * fill.avg_fill_price,
            "avg_fill_price": fill.avg_fill_price,
            "fees_paid": fill.fees_paid,
            "fee_percentage": (fill.fees_paid / (fill.filled_qty * fill.avg_fill_price) * 100)
                            if fill.filled_qty > 0 else 0,
            "time_since_fill": (datetime.now() - fill.last_fill_time).total_seconds()
        }
    
    def get_active_partials(self) -> List[Dict[str, Any]]:
        """Get all active partial fills"""
        return [
            {
                **self.calculate_fill_metrics(fill),
                "strategy": self.strategies.get(order_id, FillStrategy.WAIT)
            }
            for order_id, fill in self.partial_fills.items()
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get partial fill statistics"""
        total_partials = len(self.fill_history)
        
        if total_partials == 0:
            return {
                "active_partials": len(self.partial_fills),
                "total_handled": 0,
                "avg_fill_percentage": 0,
                "strategy_usage": {}
            }
        
        # Calculate strategy usage
        strategy_counts = {}
        total_fill_pct = 0
        
        for record in self.fill_history:
            strategy = record.get("strategy", FillStrategy.WAIT)
            strategy_counts[strategy.value] = strategy_counts.get(strategy.value, 0) + 1
            total_fill_pct += record["fill"].fill_percentage
        
        return {
            "active_partials": len(self.partial_fills),
            "total_handled": total_partials,
            "avg_fill_percentage": round(total_fill_pct / total_partials, 2),
            "strategy_usage": strategy_counts,
            "current_strategies": {
                order_id: strategy.value 
                for order_id, strategy in self.strategies.items()
            }
        }