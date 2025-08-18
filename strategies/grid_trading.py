"""
Grid Trading Strategy
Implements fixed and dynamic grid trading with auto-compounding
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)

class GridType(Enum):
    FIXED = "fixed"  # Fixed spacing between levels
    DYNAMIC = "dynamic"  # Adjusts based on volatility
    GEOMETRIC = "geometric"  # Percentage-based spacing
    FIBONACCI = "fibonacci"  # Fibonacci-based levels

class GridDirection(Enum):
    NEUTRAL = "neutral"  # Both buy and sell grids
    LONG = "long"  # Only buy grids (bullish)
    SHORT = "short"  # Only sell grids (bearish)

@dataclass
class GridLevel:
    """Individual grid level"""
    price: float
    quantity: float
    side: str  # Buy or Sell
    order_id: Optional[str] = None
    filled: bool = False
    fill_time: Optional[datetime] = None
    profit: float = 0.0

@dataclass
class GridConfig:
    """Grid trading configuration"""
    symbol: str
    grid_type: GridType
    direction: GridDirection
    upper_price: float
    lower_price: float
    grid_levels: int
    total_investment: float
    leverage: float = 1.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    auto_compound: bool = True
    compound_threshold: float = 100  # Min profit to compound
    max_open_orders: int = 50
    volatility_adjustment: bool = True
    rebalance_interval: timedelta = timedelta(hours=4)

class GridTradingStrategy:
    """Advanced grid trading strategy with dynamic adjustments"""
    
    def __init__(self, trading_client, config: GridConfig):
        """
        Initialize Grid Trading Strategy
        
        Args:
            trading_client: Trading client for order execution
            config: Grid configuration
        """
        self.client = trading_client
        self.config = config
        self.grid_levels: List[GridLevel] = []
        self.active_orders: Dict[str, GridLevel] = {}
        self.completed_trades = []
        self.total_profit = 0.0
        self.grid_active = False
        self.last_rebalance = datetime.now()
        self.statistics = {
            "grids_filled": 0,
            "total_volume": 0,
            "win_rate": 0,
            "avg_profit_per_grid": 0,
            "compounds_executed": 0
        }
        
    def calculate_grid_levels(self) -> List[GridLevel]:
        """
        Calculate grid levels based on configuration
        
        Returns:
            List of grid levels
        """
        levels = []
        
        if self.config.grid_type == GridType.FIXED:
            levels = self._calculate_fixed_grid()
        elif self.config.grid_type == GridType.DYNAMIC:
            levels = self._calculate_dynamic_grid()
        elif self.config.grid_type == GridType.GEOMETRIC:
            levels = self._calculate_geometric_grid()
        elif self.config.grid_type == GridType.FIBONACCI:
            levels = self._calculate_fibonacci_grid()
        
        return levels
    
    def _calculate_fixed_grid(self) -> List[GridLevel]:
        """Calculate fixed spacing grid levels"""
        levels = []
        price_range = self.config.upper_price - self.config.lower_price
        spacing = price_range / (self.config.grid_levels - 1)
        
        # Calculate quantity per level
        qty_per_level = self.config.total_investment / self.config.grid_levels / self.config.upper_price
        
        for i in range(self.config.grid_levels):
            price = self.config.lower_price + (spacing * i)
            
            # Determine side based on current price and direction
            if self.config.direction == GridDirection.NEUTRAL:
                # Place buys below mid-point, sells above
                mid_price = (self.config.upper_price + self.config.lower_price) / 2
                side = "Buy" if price < mid_price else "Sell"
            elif self.config.direction == GridDirection.LONG:
                side = "Buy"
            else:  # SHORT
                side = "Sell"
            
            level = GridLevel(
                price=round(price, 2),
                quantity=round(qty_per_level * self.config.leverage, 4),
                side=side
            )
            levels.append(level)
        
        return levels
    
    def _calculate_dynamic_grid(self) -> List[GridLevel]:
        """Calculate dynamic grid based on volatility"""
        # Get current volatility
        volatility = self._calculate_volatility()
        
        # Adjust spacing based on volatility
        base_spacing = (self.config.upper_price - self.config.lower_price) / (self.config.grid_levels - 1)
        adjusted_spacing = base_spacing * (1 + volatility)
        
        levels = []
        qty_per_level = self.config.total_investment / self.config.grid_levels / self.config.upper_price
        
        current_price = self.config.lower_price
        for i in range(self.config.grid_levels):
            if i > 0:
                # Vary spacing based on position in range
                position_factor = i / self.config.grid_levels
                spacing = adjusted_spacing * (1 + position_factor * volatility)
                current_price += spacing
            
            if current_price > self.config.upper_price:
                current_price = self.config.upper_price
            
            # Determine side
            mid_price = (self.config.upper_price + self.config.lower_price) / 2
            side = "Buy" if current_price < mid_price else "Sell"
            
            level = GridLevel(
                price=round(current_price, 2),
                quantity=round(qty_per_level * self.config.leverage, 4),
                side=side
            )
            levels.append(level)
        
        return levels
    
    def _calculate_geometric_grid(self) -> List[GridLevel]:
        """Calculate geometric (percentage-based) grid"""
        levels = []
        
        # Calculate geometric ratio
        ratio = (self.config.upper_price / self.config.lower_price) ** (1 / (self.config.grid_levels - 1))
        
        qty_per_level = self.config.total_investment / self.config.grid_levels / self.config.upper_price
        
        for i in range(self.config.grid_levels):
            price = self.config.lower_price * (ratio ** i)
            
            # Determine side
            mid_price = (self.config.upper_price + self.config.lower_price) / 2
            side = "Buy" if price < mid_price else "Sell"
            
            level = GridLevel(
                price=round(price, 2),
                quantity=round(qty_per_level * self.config.leverage, 4),
                side=side
            )
            levels.append(level)
        
        return levels
    
    def _calculate_fibonacci_grid(self) -> List[GridLevel]:
        """Calculate Fibonacci-based grid levels"""
        # Fibonacci ratios
        fib_ratios = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
        
        # Extend if need more levels
        while len(fib_ratios) < self.config.grid_levels:
            fib_ratios.append(fib_ratios[-1] + 0.1)
        
        levels = []
        price_range = self.config.upper_price - self.config.lower_price
        qty_per_level = self.config.total_investment / self.config.grid_levels / self.config.upper_price
        
        for i in range(min(self.config.grid_levels, len(fib_ratios))):
            price = self.config.lower_price + (price_range * fib_ratios[i])
            
            # Determine side
            mid_price = (self.config.upper_price + self.config.lower_price) / 2
            side = "Buy" if price < mid_price else "Sell"
            
            level = GridLevel(
                price=round(price, 2),
                quantity=round(qty_per_level * self.config.leverage, 4),
                side=side
            )
            levels.append(level)
        
        return levels
    
    async def start_grid(self):
        """Start the grid trading strategy"""
        try:
            logger.info(f"Starting {self.config.grid_type.value} grid for {self.config.symbol}")
            
            # Calculate initial grid levels
            self.grid_levels = self.calculate_grid_levels()
            
            # Place initial orders
            await self._place_grid_orders()
            
            self.grid_active = True
            
            # Start monitoring
            asyncio.create_task(self._monitor_grid())
            
            logger.info(f"Grid trading started with {len(self.grid_levels)} levels")
            
        except Exception as e:
            logger.error(f"Error starting grid: {e}")
            raise
    
    async def _place_grid_orders(self):
        """Place all grid orders"""
        placed_count = 0
        
        for level in self.grid_levels:
            if level.filled or level.order_id:
                continue
            
            # Check max open orders limit
            if placed_count >= self.config.max_open_orders:
                break
            
            try:
                # Place limit order
                order_params = {
                    "category": "linear",
                    "symbol": self.config.symbol,
                    "side": level.side,
                    "orderType": "Limit",
                    "qty": str(level.quantity),
                    "price": str(level.price),
                    "timeInForce": "GTC",
                    "reduceOnly": False
                }
                
                result = await self.client.place_order(**order_params)
                
                if result["retCode"] == 0:
                    level.order_id = result["result"]["orderId"]
                    self.active_orders[level.order_id] = level
                    placed_count += 1
                    logger.debug(f"Placed grid order at {level.price}: {level.order_id}")
                else:
                    logger.error(f"Failed to place grid order: {result}")
                    
            except Exception as e:
                logger.error(f"Error placing grid order: {e}")
    
    async def _monitor_grid(self):
        """Monitor grid orders and handle fills"""
        while self.grid_active:
            try:
                # Check for filled orders
                await self._check_filled_orders()
                
                # Rebalance if needed
                if datetime.now() - self.last_rebalance > self.config.rebalance_interval:
                    await self._rebalance_grid()
                
                # Check for auto-compound
                if self.config.auto_compound:
                    await self._check_compound()
                
                # Update statistics
                self._update_statistics()
                
                # Wait before next check
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Error monitoring grid: {e}")
    
    async def _check_filled_orders(self):
        """Check for filled orders and place counter orders"""
        try:
            # Get open orders
            open_orders = await self.client.get_open_orders(
                category="linear",
                symbol=self.config.symbol
            )
            
            if open_orders["retCode"] != 0:
                return
            
            open_order_ids = {order["orderId"] for order in open_orders["result"]["list"]}
            
            # Check for filled orders
            for order_id, level in list(self.active_orders.items()):
                if order_id not in open_order_ids:
                    # Order was filled
                    await self._handle_filled_order(order_id, level)
            
        except Exception as e:
            logger.error(f"Error checking filled orders: {e}")
    
    async def _handle_filled_order(self, order_id: str, level: GridLevel):
        """Handle a filled grid order"""
        try:
            level.filled = True
            level.fill_time = datetime.now()
            
            # Calculate profit (simplified - would need actual fill price)
            if level.side == "Sell":
                # Profit from selling at higher price
                level.profit = level.quantity * (level.price - self.config.lower_price) * 0.001
            else:
                # Profit from buying at lower price
                level.profit = level.quantity * (self.config.upper_price - level.price) * 0.001
            
            self.total_profit += level.profit
            self.statistics["grids_filled"] += 1
            
            # Remove from active orders
            del self.active_orders[order_id]
            
            # Place counter order (opposite side at different level)
            await self._place_counter_order(level)
            
            logger.info(f"Grid filled at {level.price}, profit: ${level.profit:.2f}")
            
        except Exception as e:
            logger.error(f"Error handling filled order: {e}")
    
    async def _place_counter_order(self, filled_level: GridLevel):
        """Place a counter order after a fill"""
        try:
            # Find appropriate counter level
            counter_side = "Sell" if filled_level.side == "Buy" else "Buy"
            
            # Find unfilled level on opposite side
            for level in self.grid_levels:
                if not level.filled and level.side == counter_side and not level.order_id:
                    # Place order at this level
                    order_params = {
                        "category": "linear",
                        "symbol": self.config.symbol,
                        "side": level.side,
                        "orderType": "Limit",
                        "qty": str(level.quantity),
                        "price": str(level.price),
                        "timeInForce": "GTC"
                    }
                    
                    result = await self.client.place_order(**order_params)
                    
                    if result["retCode"] == 0:
                        level.order_id = result["result"]["orderId"]
                        self.active_orders[level.order_id] = level
                        logger.debug(f"Placed counter order at {level.price}")
                    
                    break
                    
        except Exception as e:
            logger.error(f"Error placing counter order: {e}")
    
    async def _rebalance_grid(self):
        """Rebalance grid based on market conditions"""
        try:
            if not self.config.volatility_adjustment:
                return
            
            logger.info("Rebalancing grid...")
            
            # Get current market price
            ticker = await self.client.get_tickers(
                category="linear",
                symbol=self.config.symbol
            )
            
            if ticker["retCode"] != 0:
                return
            
            current_price = float(ticker["result"]["list"][0]["lastPrice"])
            
            # Check if price is outside grid range
            if current_price > self.config.upper_price * 1.1:
                # Price broke above - shift grid up
                shift_amount = current_price - self.config.upper_price
                await self._shift_grid(shift_amount)
            elif current_price < self.config.lower_price * 0.9:
                # Price broke below - shift grid down
                shift_amount = self.config.lower_price - current_price
                await self._shift_grid(-shift_amount)
            
            # Adjust grid density based on volatility
            volatility = self._calculate_volatility()
            if volatility > 0.03:  # High volatility
                # Widen grid spacing
                await self._adjust_grid_spacing(1.2)
            elif volatility < 0.01:  # Low volatility
                # Tighten grid spacing
                await self._adjust_grid_spacing(0.8)
            
            self.last_rebalance = datetime.now()
            
        except Exception as e:
            logger.error(f"Error rebalancing grid: {e}")
    
    async def _shift_grid(self, shift_amount: float):
        """Shift entire grid up or down"""
        try:
            # Cancel all active orders
            await self._cancel_all_orders()
            
            # Shift price range
            self.config.upper_price += shift_amount
            self.config.lower_price += shift_amount
            
            # Recalculate grid levels
            self.grid_levels = self.calculate_grid_levels()
            
            # Place new orders
            await self._place_grid_orders()
            
            logger.info(f"Grid shifted by ${shift_amount:.2f}")
            
        except Exception as e:
            logger.error(f"Error shifting grid: {e}")
    
    async def _adjust_grid_spacing(self, factor: float):
        """Adjust grid spacing by a factor"""
        try:
            # Cancel all active orders
            await self._cancel_all_orders()
            
            # Adjust range
            mid_price = (self.config.upper_price + self.config.lower_price) / 2
            half_range = (self.config.upper_price - self.config.lower_price) / 2
            
            self.config.upper_price = mid_price + (half_range * factor)
            self.config.lower_price = mid_price - (half_range * factor)
            
            # Recalculate grid levels
            self.grid_levels = self.calculate_grid_levels()
            
            # Place new orders
            await self._place_grid_orders()
            
            logger.info(f"Grid spacing adjusted by factor {factor}")
            
        except Exception as e:
            logger.error(f"Error adjusting grid spacing: {e}")
    
    async def _check_compound(self):
        """Check if profits should be compounded"""
        try:
            if self.total_profit >= self.config.compound_threshold:
                # Calculate additional investment
                compound_amount = self.total_profit * 0.5  # Compound 50% of profits
                
                # Increase grid quantities
                increase_factor = 1 + (compound_amount / self.config.total_investment)
                
                for level in self.grid_levels:
                    level.quantity *= increase_factor
                
                # Update config
                self.config.total_investment += compound_amount
                
                # Reset profit counter
                self.total_profit -= compound_amount
                
                self.statistics["compounds_executed"] += 1
                
                logger.info(f"Compounded ${compound_amount:.2f} into grid")
                
        except Exception as e:
            logger.error(f"Error checking compound: {e}")
    
    async def _cancel_all_orders(self):
        """Cancel all active grid orders"""
        try:
            for order_id in list(self.active_orders.keys()):
                await self.client.cancel_order(
                    category="linear",
                    symbol=self.config.symbol,
                    orderId=order_id
                )
                
                # Reset level
                level = self.active_orders[order_id]
                level.order_id = None
                del self.active_orders[order_id]
            
            logger.info(f"Cancelled {len(self.active_orders)} orders")
            
        except Exception as e:
            logger.error(f"Error cancelling orders: {e}")
    
    def _calculate_volatility(self) -> float:
        """Calculate current market volatility"""
        # Simplified volatility calculation
        # In production, would use historical price data
        return 0.02  # 2% volatility as placeholder
    
    def _update_statistics(self):
        """Update trading statistics"""
        if self.statistics["grids_filled"] > 0:
            self.statistics["avg_profit_per_grid"] = (
                self.total_profit / self.statistics["grids_filled"]
            )
            
            # Calculate win rate
            winning_grids = sum(1 for level in self.grid_levels if level.profit > 0)
            total_completed = sum(1 for level in self.grid_levels if level.filled)
            
            if total_completed > 0:
                self.statistics["win_rate"] = (winning_grids / total_completed) * 100
    
    async def stop_grid(self):
        """Stop the grid trading strategy"""
        try:
            logger.info("Stopping grid trading...")
            
            self.grid_active = False
            
            # Cancel all orders
            await self._cancel_all_orders()
            
            # Log final statistics
            logger.info(f"Grid stopped. Total profit: ${self.total_profit:.2f}")
            logger.info(f"Statistics: {self.statistics}")
            
        except Exception as e:
            logger.error(f"Error stopping grid: {e}")
    
    def get_grid_status(self) -> Dict[str, Any]:
        """Get current grid status"""
        return {
            "active": self.grid_active,
            "symbol": self.config.symbol,
            "type": self.config.grid_type.value,
            "direction": self.config.direction.value,
            "levels": len(self.grid_levels),
            "active_orders": len(self.active_orders),
            "filled_orders": self.statistics["grids_filled"],
            "total_profit": round(self.total_profit, 2),
            "investment": round(self.config.total_investment, 2),
            "roi": round((self.total_profit / self.config.total_investment) * 100, 2)
                   if self.config.total_investment > 0 else 0,
            "statistics": self.statistics
        }
    
    def get_grid_levels_display(self) -> List[Dict[str, Any]]:
        """Get grid levels for display"""
        return [
            {
                "price": level.price,
                "quantity": level.quantity,
                "side": level.side,
                "filled": level.filled,
                "profit": round(level.profit, 2),
                "order_id": level.order_id
            }
            for level in self.grid_levels
        ]