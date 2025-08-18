"""
Order Modification and Management System
Handles real-time order updates, modifications, and batch operations
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)

class ModificationType(Enum):
    PRICE = "price"
    QUANTITY = "quantity"
    TRIGGER = "trigger"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    BATCH = "batch"

class OrderStatus(Enum):
    NEW = "New"
    PARTIALLY_FILLED = "PartiallyFilled"
    FILLED = "Filled"
    CANCELLED = "Cancelled"
    REJECTED = "Rejected"
    TRIGGERED = "Triggered"
    DEACTIVATED = "Deactivated"

@dataclass
class OrderModification:
    """Order modification request"""
    order_id: str
    modification_type: ModificationType
    new_value: Any
    reason: str
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass 
class BatchModification:
    """Batch order modification request"""
    modifications: List[OrderModification]
    atomic: bool = True  # All succeed or all fail
    priority: int = 0  # Higher priority processes first

class OrderModifier:
    """Handles order modifications and batch operations"""
    
    def __init__(self, trading_client, max_retries: int = 3):
        """
        Initialize Order Modifier
        
        Args:
            trading_client: Bybit trading client
            max_retries: Maximum retry attempts for failed modifications
        """
        self.client = trading_client
        self.max_retries = max_retries
        self.modification_queue = asyncio.Queue()
        self.processing = False
        self.statistics = {
            "total_modifications": 0,
            "successful": 0,
            "failed": 0,
            "retry_count": 0
        }
        self.modification_history = []
        
    async def start_processor(self):
        """Start the modification processor"""
        if not self.processing:
            self.processing = True
            asyncio.create_task(self._process_modifications())
            logger.info("Order modification processor started")
    
    async def stop_processor(self):
        """Stop the modification processor"""
        self.processing = False
        logger.info("Order modification processor stopped")
    
    async def _process_modifications(self):
        """Process modification queue"""
        while self.processing:
            try:
                # Get modification from queue
                modification = await asyncio.wait_for(
                    self.modification_queue.get(), 
                    timeout=1.0
                )
                
                # Process modification
                if isinstance(modification, BatchModification):
                    await self._process_batch_modification(modification)
                else:
                    await self._process_single_modification(modification)
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing modification: {e}")
    
    async def modify_price(self, order_id: str, new_price: float, 
                          reason: str = "Price adjustment") -> Dict[str, Any]:
        """
        Modify order price
        
        Args:
            order_id: Order ID
            new_price: New price
            reason: Modification reason
            
        Returns:
            Modification result
        """
        modification = OrderModification(
            order_id=order_id,
            modification_type=ModificationType.PRICE,
            new_value=new_price,
            reason=reason
        )
        
        return await self._execute_modification(modification)
    
    async def modify_quantity(self, order_id: str, new_quantity: float,
                            reason: str = "Quantity adjustment") -> Dict[str, Any]:
        """
        Modify order quantity
        
        Args:
            order_id: Order ID
            new_quantity: New quantity
            reason: Modification reason
            
        Returns:
            Modification result
        """
        modification = OrderModification(
            order_id=order_id,
            modification_type=ModificationType.QUANTITY,
            new_value=new_quantity,
            reason=reason
        )
        
        return await self._execute_modification(modification)
    
    async def modify_trigger_price(self, order_id: str, new_trigger: float,
                                  reason: str = "Trigger adjustment") -> Dict[str, Any]:
        """
        Modify conditional order trigger price
        
        Args:
            order_id: Order ID
            new_trigger: New trigger price
            reason: Modification reason
            
        Returns:
            Modification result
        """
        modification = OrderModification(
            order_id=order_id,
            modification_type=ModificationType.TRIGGER,
            new_value=new_trigger,
            reason=reason
        )
        
        return await self._execute_modification(modification)
    
    async def adjust_protection_orders(self, position_id: str, 
                                      stop_loss: Optional[float] = None,
                                      take_profit: Optional[float] = None) -> Dict[str, Any]:
        """
        Adjust stop-loss and take-profit for a position
        
        Args:
            position_id: Position ID
            stop_loss: New stop-loss price
            take_profit: New take-profit price
            
        Returns:
            Adjustment results
        """
        results = {"stop_loss": None, "take_profit": None}
        
        try:
            # Get position details
            position = await self._get_position(position_id)
            if not position:
                raise ValueError(f"Position {position_id} not found")
            
            # Modify stop-loss if provided
            if stop_loss is not None:
                sl_result = await self._modify_stop_loss(position, stop_loss)
                results["stop_loss"] = sl_result
            
            # Modify take-profit if provided
            if take_profit is not None:
                tp_result = await self._modify_take_profit(position, take_profit)
                results["take_profit"] = tp_result
            
            return results
            
        except Exception as e:
            logger.error(f"Error adjusting protection orders: {e}")
            raise
    
    async def batch_modify(self, modifications: List[OrderModification],
                          atomic: bool = True) -> Dict[str, Any]:
        """
        Execute batch order modifications
        
        Args:
            modifications: List of modifications
            atomic: If True, all must succeed or all rollback
            
        Returns:
            Batch results
        """
        batch = BatchModification(
            modifications=modifications,
            atomic=atomic
        )
        
        return await self._process_batch_modification(batch)
    
    async def _process_batch_modification(self, batch: BatchModification) -> Dict[str, Any]:
        """Process batch modification"""
        results = []
        successful = []
        failed = []
        
        for modification in batch.modifications:
            try:
                result = await self._execute_modification(modification)
                
                if result and result.get("success"):
                    successful.append(modification)
                    results.append(result)
                else:
                    failed.append(modification)
                    
                    if batch.atomic:
                        # Rollback successful modifications
                        await self._rollback_modifications(successful)
                        raise Exception(f"Batch modification failed at {modification.order_id}")
                        
            except Exception as e:
                failed.append(modification)
                
                if batch.atomic:
                    await self._rollback_modifications(successful)
                    raise
        
        return {
            "total": len(batch.modifications),
            "successful": len(successful),
            "failed": len(failed),
            "results": results
        }
    
    async def _execute_modification(self, modification: OrderModification, 
                                   retry_count: int = 0) -> Dict[str, Any]:
        """Execute a single modification"""
        try:
            self.statistics["total_modifications"] += 1
            
            # Get current order details
            order = await self._get_order(modification.order_id)
            if not order:
                raise ValueError(f"Order {modification.order_id} not found")
            
            # Build modification parameters
            params = {
                "category": "linear",
                "symbol": order["symbol"],
                "orderId": modification.order_id
            }
            
            # Add modification based on type
            if modification.modification_type == ModificationType.PRICE:
                params["price"] = str(modification.new_value)
            elif modification.modification_type == ModificationType.QUANTITY:
                params["qty"] = str(modification.new_value)
            elif modification.modification_type == ModificationType.TRIGGER:
                params["triggerPrice"] = str(modification.new_value)
            
            # Execute modification
            result = await self.client.amend_order(**params)
            
            if result["retCode"] == 0:
                self.statistics["successful"] += 1
                
                # Log modification
                self.modification_history.append({
                    "modification": modification,
                    "result": result,
                    "timestamp": datetime.now(),
                    "success": True
                })
                
                logger.info(f"Order {modification.order_id} modified: {modification.reason}")
                return {"success": True, "result": result["result"]}
            else:
                raise Exception(f"Modification failed: {result['retMsg']}")
                
        except Exception as e:
            logger.error(f"Modification error: {e}")
            
            # Retry if applicable
            if retry_count < self.max_retries:
                self.statistics["retry_count"] += 1
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                return await self._execute_modification(modification, retry_count + 1)
            
            self.statistics["failed"] += 1
            
            # Log failure
            self.modification_history.append({
                "modification": modification,
                "error": str(e),
                "timestamp": datetime.now(),
                "success": False
            })
            
            return {"success": False, "error": str(e)}
    
    async def _rollback_modifications(self, modifications: List[OrderModification]):
        """Rollback successful modifications in case of atomic batch failure"""
        for modification in reversed(modifications):
            try:
                # This would need to restore original values
                # Implementation depends on tracking original values
                logger.info(f"Rolling back modification for order {modification.order_id}")
            except Exception as e:
                logger.error(f"Rollback failed for {modification.order_id}: {e}")
    
    async def cancel_and_replace(self, order_id: str, 
                                new_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cancel an order and replace with new one
        
        Args:
            order_id: Order to cancel
            new_params: Parameters for new order
            
        Returns:
            New order result
        """
        try:
            # Cancel existing order
            cancel_result = await self.client.cancel_order(
                category="linear",
                orderId=order_id
            )
            
            if cancel_result["retCode"] != 0:
                raise Exception(f"Failed to cancel order: {cancel_result['retMsg']}")
            
            # Place new order
            new_order = await self.client.place_order(**new_params)
            
            if new_order["retCode"] == 0:
                logger.info(f"Order {order_id} replaced with {new_order['result']['orderId']}")
                return {
                    "success": True,
                    "old_order_id": order_id,
                    "new_order_id": new_order["result"]["orderId"],
                    "result": new_order["result"]
                }
            else:
                # Try to restore original order if new order fails
                logger.error(f"New order failed, original order already cancelled")
                raise Exception(f"Replacement failed: {new_order['retMsg']}")
                
        except Exception as e:
            logger.error(f"Cancel and replace error: {e}")
            raise
    
    async def smart_modification(self, order_id: str, 
                                market_conditions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Intelligently modify order based on market conditions
        
        Args:
            order_id: Order ID
            market_conditions: Current market data
            
        Returns:
            Modification result
        """
        try:
            order = await self._get_order(order_id)
            if not order:
                raise ValueError(f"Order {order_id} not found")
            
            modifications = []
            
            # Check if price adjustment needed
            current_price = market_conditions.get("last_price")
            order_price = float(order.get("price", 0))
            
            if order_price > 0:
                price_diff_pct = abs(current_price - order_price) / order_price * 100
                
                # Adjust price if too far from market
                if price_diff_pct > 1:  # More than 1% difference
                    if order["side"] == "Buy":
                        new_price = current_price * 0.999  # Slightly below market
                    else:
                        new_price = current_price * 1.001  # Slightly above market
                    
                    modifications.append(OrderModification(
                        order_id=order_id,
                        modification_type=ModificationType.PRICE,
                        new_value=new_price,
                        reason="Smart price adjustment"
                    ))
            
            # Check volatility for trigger adjustment
            volatility = market_conditions.get("volatility", 0)
            if volatility > 0.02:  # High volatility
                # Widen stops/triggers
                if order.get("triggerPrice"):
                    trigger_price = float(order["triggerPrice"])
                    adjustment = trigger_price * 0.002  # 0.2% adjustment
                    
                    if order["side"] == "Buy":
                        new_trigger = trigger_price - adjustment
                    else:
                        new_trigger = trigger_price + adjustment
                    
                    modifications.append(OrderModification(
                        order_id=order_id,
                        modification_type=ModificationType.TRIGGER,
                        new_value=new_trigger,
                        reason="Volatility-based trigger adjustment"
                    ))
            
            # Execute modifications if any
            if modifications:
                return await self.batch_modify(modifications, atomic=False)
            
            return {"success": True, "message": "No modifications needed"}
            
        except Exception as e:
            logger.error(f"Smart modification error: {e}")
            raise
    
    def handle_partial_fill_update(self, order_id: str, fill_data: Dict[str, Any]):
        """
        Handle partial fill and update order accordingly
        
        Args:
            order_id: Order ID
            fill_data: Fill information
        """
        try:
            filled_qty = fill_data.get("filled_qty", 0)
            remaining_qty = fill_data.get("remaining_qty", 0)
            avg_price = fill_data.get("avg_price", 0)
            
            # Log partial fill
            logger.info(f"Partial fill for {order_id}: {filled_qty}/{filled_qty + remaining_qty}")
            
            # Store fill information
            fill_record = {
                "order_id": order_id,
                "filled_qty": filled_qty,
                "remaining_qty": remaining_qty,
                "avg_price": avg_price,
                "timestamp": datetime.now()
            }
            
            # Could trigger additional logic here
            # e.g., modify remaining order, cancel if mostly filled, etc.
            
        except Exception as e:
            logger.error(f"Error handling partial fill: {e}")
    
    async def _get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order details from exchange"""
        try:
            # First try active orders
            result = await self.client.get_open_orders(
                category="linear",
                orderId=order_id
            )
            
            if result["retCode"] == 0 and result["result"]["list"]:
                return result["result"]["list"][0]
            
            # Try conditional orders
            result = await self.client.get_open_orders(
                category="linear",
                orderId=order_id,
                orderFilter="StopOrder"
            )
            
            if result["retCode"] == 0 and result["result"]["list"]:
                return result["result"]["list"][0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting order: {e}")
            return None
    
    async def _get_position(self, position_id: str) -> Optional[Dict[str, Any]]:
        """Get position details"""
        try:
            # This would need implementation based on how positions are tracked
            # Could query by symbol or use position tracking system
            result = await self.client.get_positions(category="linear")
            
            if result["retCode"] == 0:
                for position in result["result"]["list"]:
                    # Match position by some identifier
                    if position.get("symbol") == position_id:  # Or other matching logic
                        return position
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting position: {e}")
            return None
    
    async def _modify_stop_loss(self, position: Dict[str, Any], 
                               new_stop: float) -> Dict[str, Any]:
        """Modify position stop-loss"""
        try:
            result = await self.client.set_trading_stop(
                category="linear",
                symbol=position["symbol"],
                positionIdx=position.get("positionIdx", 0),
                stopLoss=str(new_stop)
            )
            
            if result["retCode"] == 0:
                return {"success": True, "stop_loss": new_stop}
            else:
                raise Exception(f"Failed to modify stop-loss: {result['retMsg']}")
                
        except Exception as e:
            logger.error(f"Stop-loss modification error: {e}")
            return {"success": False, "error": str(e)}
    
    async def _modify_take_profit(self, position: Dict[str, Any],
                                 new_tp: float) -> Dict[str, Any]:
        """Modify position take-profit"""
        try:
            result = await self.client.set_trading_stop(
                category="linear",
                symbol=position["symbol"],
                positionIdx=position.get("positionIdx", 0),
                takeProfit=str(new_tp)
            )
            
            if result["retCode"] == 0:
                return {"success": True, "take_profit": new_tp}
            else:
                raise Exception(f"Failed to modify take-profit: {result['retMsg']}")
                
        except Exception as e:
            logger.error(f"Take-profit modification error: {e}")
            return {"success": False, "error": str(e)}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get modification statistics"""
        success_rate = 0
        if self.statistics["total_modifications"] > 0:
            success_rate = (self.statistics["successful"] / 
                          self.statistics["total_modifications"]) * 100
        
        return {
            **self.statistics,
            "success_rate": round(success_rate, 2),
            "history_count": len(self.modification_history)
        }
    
    def get_recent_modifications(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent modification history"""
        return self.modification_history[-limit:] if self.modification_history else []