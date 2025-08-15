"""
Database package for Bybit Trading Bot
Provides models, service layer, and migration utilities
"""

from .models import (
    Base, User, APIKey, Strategy, Trade, Position, Order,
    MarketData, Signal, Alert, SystemLog, Performance,
    UserRole, OrderStatus, OrderSide, OrderType, PositionStatus,
    init_database
)

from .service import DatabaseService, get_db_service

__all__ = [
    # Models
    'Base', 'User', 'APIKey', 'Strategy', 'Trade', 'Position', 'Order',
    'MarketData', 'Signal', 'Alert', 'SystemLog', 'Performance',
    
    # Enums
    'UserRole', 'OrderStatus', 'OrderSide', 'OrderType', 'PositionStatus',
    
    # Functions
    'init_database', 'DatabaseService', 'get_db_service'
]