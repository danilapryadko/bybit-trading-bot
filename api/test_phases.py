"""
Test endpoints for Phase 7 & 8 features
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import logging
import asyncio
from datetime import datetime

# Import Phase 7 & 8 modules
from orders import (
    AdvancedOrderManager,
    StopLossOrder,
    TakeProfitOrder,
    TrailingStopConfig,
    TrailingMethod,
    OrderModifier,
    PartialFillHandler
)
from strategies.grid_trading import (
    GridTradingStrategy,
    GridConfig,
    GridType,
    GridDirection
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/test", tags=["testing"])

# Mock client for testing
class TestClient:
    """Test client for demo purposes"""
    
    def __init__(self):
        self.test_mode = True
        self.orders = []
        
    async def place_order(self, **kwargs):
        order_id = f"test_{datetime.now().timestamp()}"
        self.orders.append({
            "orderId": order_id,
            **kwargs
        })
        return {
            "retCode": 0,
            "result": {"orderId": order_id}
        }
    
    async def get_tickers(self, **kwargs):
        return {
            "retCode": 0,
            "result": {
                "list": [{
                    "symbol": "BTCUSDT",
                    "lastPrice": "50000"
                }]
            }
        }
    
    async def cancel_order(self, **kwargs):
        return {"retCode": 0}
    
    async def get_open_orders(self, **kwargs):
        return {
            "retCode": 0,
            "result": {"list": self.orders}
        }

# Create test instances
test_client = TestClient()
order_manager = AdvancedOrderManager(test_client)
order_modifier = OrderModifier(test_client)
fill_handler = PartialFillHandler(test_client, order_modifier)

@router.get("/status")
async def test_status():
    """Get test environment status"""
    return {
        "status": "active",
        "phase_7": "Advanced Orders Ready",
        "phase_8": "Grid Trading Ready",
        "test_mode": True,
        "timestamp": datetime.now().isoformat()
    }

@router.post("/phase7/stop-loss")
async def test_stop_loss(
    symbol: str = "BTCUSDT",
    position_size: float = 0.1,
    trigger_price: float = 49000
):
    """Test stop-loss order placement"""
    try:
        stop_loss = StopLossOrder(
            symbol=symbol,
            side="Sell",
            quantity=position_size,
            trigger_price=trigger_price
        )
        
        result = await order_manager.place_stop_loss("test_position", stop_loss)
        
        return {
            "success": True,
            "message": "Stop-loss order placed",
            "order": result,
            "trigger_price": trigger_price,
            "protection_type": "stop_loss"
        }
    except Exception as e:
        logger.error(f"Stop-loss test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/phase7/take-profit")
async def test_take_profit(
    symbol: str = "BTCUSDT",
    position_size: float = 0.1,
    trigger_price: float = 52000
):
    """Test take-profit order placement"""
    try:
        take_profit = TakeProfitOrder(
            symbol=symbol,
            side="Sell",
            quantity=position_size,
            trigger_price=trigger_price
        )
        
        result = await order_manager.place_take_profit("test_position", take_profit)
        
        return {
            "success": True,
            "message": "Take-profit order placed",
            "order": result,
            "trigger_price": trigger_price,
            "protection_type": "take_profit"
        }
    except Exception as e:
        logger.error(f"Take-profit test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/phase7/trailing-stop")
async def test_trailing_stop(
    symbol: str = "BTCUSDT",
    position_size: float = 0.1,
    trail_percent: float = 2.0
):
    """Test trailing stop setup"""
    try:
        config = TrailingStopConfig(
            symbol=symbol,
            side="Sell",
            quantity=position_size,
            method=TrailingMethod.PERCENTAGE,
            trail_value=trail_percent
        )
        
        trail_id = await order_manager.setup_trailing_stop("test_position", config)
        
        return {
            "success": True,
            "message": "Trailing stop configured",
            "trail_id": trail_id,
            "trail_percent": trail_percent,
            "method": "percentage"
        }
    except Exception as e:
        logger.error(f"Trailing stop test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/phase7/statistics")
async def get_order_statistics():
    """Get advanced order statistics"""
    try:
        stats = order_manager.get_statistics()
        modifier_stats = order_modifier.get_statistics()
        fill_stats = fill_handler.get_statistics()
        
        return {
            "order_manager": stats,
            "modifier": modifier_stats,
            "fill_handler": fill_stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Statistics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/phase8/grid/create")
async def create_grid(
    symbol: str = "BTCUSDT",
    upper_price: float = 52000,
    lower_price: float = 48000,
    grid_levels: int = 10,
    investment: float = 1000,
    grid_type: str = "fixed"
):
    """Create a grid trading strategy"""
    try:
        # Map grid type
        type_map = {
            "fixed": GridType.FIXED,
            "dynamic": GridType.DYNAMIC,
            "geometric": GridType.GEOMETRIC,
            "fibonacci": GridType.FIBONACCI
        }
        
        config = GridConfig(
            symbol=symbol,
            grid_type=type_map.get(grid_type, GridType.FIXED),
            direction=GridDirection.NEUTRAL,
            upper_price=upper_price,
            lower_price=lower_price,
            grid_levels=grid_levels,
            total_investment=investment
        )
        
        strategy = GridTradingStrategy(test_client, config)
        levels = strategy.calculate_grid_levels()
        
        return {
            "success": True,
            "message": f"Grid created with {len(levels)} levels",
            "config": {
                "symbol": symbol,
                "type": grid_type,
                "range": f"${lower_price} - ${upper_price}",
                "levels": grid_levels,
                "investment": investment
            },
            "grid_levels": [
                {
                    "price": level.price,
                    "quantity": level.quantity,
                    "side": level.side
                }
                for level in levels[:5]  # Show first 5 levels
            ]
        }
    except Exception as e:
        logger.error(f"Grid creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/phase8/grid/start")
async def start_grid_trading(
    symbol: str = "BTCUSDT",
    investment: float = 1000
):
    """Start grid trading (demo mode)"""
    try:
        config = GridConfig(
            symbol=symbol,
            grid_type=GridType.FIXED,
            direction=GridDirection.NEUTRAL,
            upper_price=51000,
            lower_price=49000,
            grid_levels=5,
            total_investment=investment
        )
        
        strategy = GridTradingStrategy(test_client, config)
        
        # Start grid (will run async)
        asyncio.create_task(strategy.start_grid())
        
        # Wait a moment for initialization
        await asyncio.sleep(0.5)
        
        status = strategy.get_grid_status()
        
        return {
            "success": True,
            "message": "Grid trading started (demo mode)",
            "status": status,
            "note": "This is a demonstration. Real trading requires live API connection."
        }
    except Exception as e:
        logger.error(f"Grid start error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/phase8/grid/types")
async def get_grid_types():
    """Get available grid types and their descriptions"""
    return {
        "grid_types": [
            {
                "type": "fixed",
                "name": "Fixed Grid",
                "description": "Equal spacing between price levels",
                "best_for": "Range-bound markets"
            },
            {
                "type": "dynamic",
                "name": "Dynamic Grid",
                "description": "Volatility-adjusted spacing",
                "best_for": "All market conditions"
            },
            {
                "type": "geometric",
                "name": "Geometric Grid",
                "description": "Percentage-based intervals",
                "best_for": "Trending markets"
            },
            {
                "type": "fibonacci",
                "name": "Fibonacci Grid",
                "description": "Natural support/resistance levels",
                "best_for": "Technical trading"
            }
        ],
        "directions": [
            {
                "type": "neutral",
                "description": "Both buy and sell orders"
            },
            {
                "type": "long",
                "description": "Only buy orders (bullish)"
            },
            {
                "type": "short",
                "description": "Only sell orders (bearish)"
            }
        ]
    }

@router.get("/features")
async def get_features_summary():
    """Get summary of all implemented features"""
    return {
        "phase_7_advanced_orders": {
            "stop_loss": "Automatic loss limiting",
            "take_profit": "Profit securing",
            "trailing_stop": "Dynamic stop adjustment",
            "order_modification": "Real-time order updates",
            "partial_fills": "Smart fill handling"
        },
        "phase_8_grid_trading": {
            "grid_types": ["fixed", "dynamic", "geometric", "fibonacci"],
            "auto_compound": "Profit reinvestment",
            "dynamic_adjustment": "Volatility-based spacing",
            "optimization": "Data-driven parameters",
            "risk_management": "Integrated protection"
        },
        "integration": {
            "websocket": "Real-time data streaming",
            "risk_management": "Portfolio protection",
            "ml_predictions": "AI-powered signals",
            "backtesting": "Strategy validation"
        }
    }