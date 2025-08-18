#!/usr/bin/env python3
"""
SQLAlchemy database models for Bybit Trading Bot
Production-ready schema with all necessary tables
"""

from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Boolean, JSON, ForeignKey, Index, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func
from datetime import datetime
import enum
import os

Base = declarative_base()

# Enums
class UserRole(enum.Enum):
    VIEWER = "viewer"
    TRADER = "trader"
    ADMIN = "admin"

class OrderStatus(enum.Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class OrderSide(enum.Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(enum.Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    STOP_LIMIT = "stop_limit"

class PositionStatus(enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    LIQUIDATED = "liquidated"

# Models
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.VIEWER)
    telegram_id = Column(String(50), unique=True, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    settings = Column(JSON, default={})
    
    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    strategies = relationship("Strategy", back_populates="user")
    trades = relationship("Trade", back_populates="user")
    positions = relationship("Position", back_populates="user")
    orders = relationship("Order", back_populates="user")
    alerts = relationship("Alert", back_populates="user")

class APIKey(Base):
    __tablename__ = 'api_keys'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    exchange = Column(String(50), nullable=False, default='bybit')
    name = Column(String(100), nullable=False)
    api_key = Column(String(255), nullable=False)  # Encrypted
    api_secret = Column(String(255), nullable=False)  # Encrypted
    is_testnet = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    permissions = Column(JSON, default={})  # {"spot": true, "futures": true, "withdraw": false}
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    # Index for quick lookup
    __table_args__ = (
        Index('idx_user_exchange_active', 'user_id', 'exchange', 'is_active'),
    )

class Strategy(Base):
    __tablename__ = 'strategies'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)  # 'ml', 'technical', 'hybrid'
    config = Column(JSON, nullable=False)  # Strategy parameters
    is_active = Column(Boolean, default=False)
    symbols = Column(JSON, default=[])  # List of trading symbols
    risk_config = Column(JSON, default={})  # Risk management settings
    performance = Column(JSON, default={})  # Performance metrics
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="strategies")
    trades = relationship("Trade", back_populates="strategy")

class Trade(Base):
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    strategy_id = Column(Integer, ForeignKey('strategies.id'), nullable=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(Enum(OrderSide), nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Float, nullable=False)
    entry_time = Column(DateTime(timezone=True), nullable=False)
    exit_time = Column(DateTime(timezone=True), nullable=True)
    pnl = Column(Float, default=0)
    pnl_percent = Column(Float, default=0)
    fees = Column(Float, default=0)
    is_paper = Column(Boolean, default=True)
    meta_data = Column(JSON, default={})  # Additional trade data
    
    # Relationships
    user = relationship("User", back_populates="trades")
    strategy = relationship("Strategy", back_populates="trades")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_user_symbol_time', 'user_id', 'symbol', 'entry_time'),
        Index('idx_strategy_performance', 'strategy_id', 'pnl'),
    )

class Position(Base):
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(Enum(OrderSide), nullable=False)
    size = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    mark_price = Column(Float, nullable=True)
    liquidation_price = Column(Float, nullable=True)
    margin = Column(Float, nullable=False)
    leverage = Column(Integer, default=1)
    unrealized_pnl = Column(Float, default=0)
    realized_pnl = Column(Float, default=0)
    status = Column(Enum(PositionStatus), default=PositionStatus.OPEN)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    trailing_stop = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="positions")
    orders = relationship("Order", back_populates="position")
    
    # Index for active positions
    __table_args__ = (
        Index('idx_user_positions_active', 'user_id', 'status', 'symbol'),
    )

class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    position_id = Column(Integer, ForeignKey('positions.id'), nullable=True)
    order_id = Column(String(100), unique=True, nullable=False, index=True)  # Exchange order ID
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(Enum(OrderSide), nullable=False)
    type = Column(Enum(OrderType), nullable=False)
    price = Column(Float, nullable=True)  # Null for market orders
    quantity = Column(Float, nullable=False)
    filled_quantity = Column(Float, default=0)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    time_in_force = Column(String(10), default='GTC')  # GTC, IOC, FOK
    reduce_only = Column(Boolean, default=False)
    close_on_trigger = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    filled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    meta_data = Column(JSON, default={})
    
    # Relationships
    user = relationship("User", back_populates="orders")
    position = relationship("Position", back_populates="orders")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_orders_active', 'user_id', 'status'),
        Index('idx_order_lookup', 'order_id', 'symbol'),
    )

class MarketData(Base):
    __tablename__ = 'market_data'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    timeframe = Column(String(10), nullable=False)  # '1m', '5m', '1h', '1d'
    
    # Composite index for efficient queries
    __table_args__ = (
        Index('idx_symbol_timeframe_timestamp', 'symbol', 'timeframe', 'timestamp'),
    )

class Signal(Base):
    __tablename__ = 'signals'
    
    id = Column(Integer, primary_key=True)
    strategy_id = Column(Integer, ForeignKey('strategies.id'), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    signal_type = Column(String(20), nullable=False)  # 'buy', 'sell', 'hold'
    strength = Column(Float, nullable=False)  # 0-1 confidence score
    price = Column(Float, nullable=False)
    meta_data = Column(JSON, default={})  # Indicators, reasons, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    executed = Column(Boolean, default=False)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Index for unexecuted signals
    __table_args__ = (
        Index('idx_signals_pending', 'executed', 'created_at'),
    )

class Alert(Base):
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    type = Column(String(50), nullable=False)  # 'trade', 'risk', 'system', 'price'
    severity = Column(String(20), nullable=False)  # 'info', 'warning', 'error', 'critical'
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    meta_data = Column(JSON, default={})
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="alerts")
    
    # Index for unread alerts
    __table_args__ = (
        Index('idx_user_alerts_unread', 'user_id', 'is_read', 'created_at'),
    )

class SystemLog(Base):
    __tablename__ = 'system_logs'
    
    id = Column(Integer, primary_key=True)
    level = Column(String(20), nullable=False, index=True)  # 'debug', 'info', 'warning', 'error'
    component = Column(String(50), nullable=False, index=True)  # 'trader', 'risk_manager', 'data_service'
    message = Column(Text, nullable=False)
    meta_data = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Index for log queries
    __table_args__ = (
        Index('idx_logs_component_time', 'component', 'created_at'),
    )

class Performance(Base):
    __tablename__ = 'performance'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    balance = Column(Float, nullable=False)
    equity = Column(Float, nullable=False)
    daily_pnl = Column(Float, default=0)
    daily_pnl_percent = Column(Float, default=0)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0)
    sharpe_ratio = Column(Float, nullable=True)
    sortino_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    meta_data = Column(JSON, default={})
    
    # Unique constraint for one record per user per day
    __table_args__ = (
        Index('idx_user_performance_date', 'user_id', 'date', unique=True),
    )

# Database initialization
def init_database(database_url=None):
    """Initialize database with all tables"""
    if database_url is None:
        database_url = os.getenv('DATABASE_URL', 'postgresql://localhost/bybit_bot')
    
    # Handle Fly.io postgres:// vs postgresql:// 
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    
    return engine, sessionmaker(bind=engine)

if __name__ == "__main__":
    # Create tables if running directly
    engine, Session = init_database()
    print("Database tables created successfully!")