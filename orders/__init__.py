"""
Advanced Order Management Module
Provides Stop-Loss, Take-Profit, Trailing Stops, and Order Modifications
"""

from .advanced_orders import (
    AdvancedOrderManager,
    StopLossOrder,
    TakeProfitOrder,
    TrailingStopConfig,
    OrderType,
    TrailingMethod
)

from .order_modifier import (
    OrderModifier,
    OrderModification,
    BatchModification,
    ModificationType,
    OrderStatus
)

from .partial_fill_handler import (
    PartialFillHandler,
    PartialFill,
    FillStrategy,
    FillHandlingConfig
)

__all__ = [
    # Advanced Orders
    'AdvancedOrderManager',
    'StopLossOrder',
    'TakeProfitOrder', 
    'TrailingStopConfig',
    'OrderType',
    'TrailingMethod',
    
    # Order Modifier
    'OrderModifier',
    'OrderModification',
    'BatchModification',
    'ModificationType',
    'OrderStatus',
    
    # Partial Fill Handler
    'PartialFillHandler',
    'PartialFill',
    'FillStrategy',
    'FillHandlingConfig'
]

__version__ = '7.0.0'