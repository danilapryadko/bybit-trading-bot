#!/usr/bin/env python3
"""
Database service layer for Bybit Trading Bot
Provides high-level interface for all database operations
"""

import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
from sqlalchemy import create_engine, and_, or_, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
import json

from .models import (
    Base, User, APIKey, Strategy, Trade, Position, Order, 
    MarketData, Signal, Alert, SystemLog, Performance,
    UserRole, OrderStatus, OrderSide, OrderType, PositionStatus
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseService:
    """Database service with all CRUD operations"""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize database connection"""
        if database_url is None:
            database_url = os.getenv('DATABASE_URL', 'postgresql://localhost/bybit_bot')
        
        # Handle Fly.io postgres:// vs postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        # Create engine with connection pooling
        self.engine = create_engine(
            database_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,  # Verify connections before using
            echo=False  # Set to True for SQL debugging
        )
        
        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
        
        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
        
        logger.info("Database service initialized")
    
    @contextmanager
    def get_session(self) -> Session:
        """Get database session with automatic cleanup"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
    
    # User Management
    def create_user(self, username: str, email: str, password_hash: str, 
                   role: UserRole = UserRole.VIEWER, telegram_id: Optional[str] = None) -> User:
        """Create new user"""
        with self.get_session() as session:
            user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                role=role,
                telegram_id=telegram_id
            )
            session.add(user)
            session.flush()
            return user
    
    def get_user(self, user_id: Optional[int] = None, username: Optional[str] = None, 
                 telegram_id: Optional[str] = None) -> Optional[User]:
        """Get user by ID, username, or telegram ID"""
        with self.get_session() as session:
            query = session.query(User)
            
            if user_id:
                return query.filter(User.id == user_id).first()
            elif username:
                return query.filter(User.username == username).first()
            elif telegram_id:
                return query.filter(User.telegram_id == telegram_id).first()
            
            return None
    
    def update_user_settings(self, user_id: int, settings: Dict[str, Any]) -> bool:
        """Update user settings"""
        with self.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                user.settings = settings
                return True
            return False
    
    # API Key Management
    def save_api_keys(self, user_id: int, api_key: str, api_secret: str, 
                     exchange: str = 'bybit', is_testnet: bool = True) -> APIKey:
        """Save encrypted API keys"""
        with self.get_session() as session:
            # Deactivate old keys
            session.query(APIKey).filter(
                and_(APIKey.user_id == user_id, APIKey.exchange == exchange)
            ).update({'is_active': False})
            
            # Create new key
            key = APIKey(
                user_id=user_id,
                exchange=exchange,
                name=f"{exchange}_{'testnet' if is_testnet else 'mainnet'}",
                api_key=api_key,  # Should be encrypted in production
                api_secret=api_secret,  # Should be encrypted in production
                is_testnet=is_testnet,
                is_active=True
            )
            session.add(key)
            session.flush()
            return key
    
    def get_active_api_keys(self, user_id: int, exchange: str = 'bybit') -> Optional[APIKey]:
        """Get active API keys for user"""
        with self.get_session() as session:
            return session.query(APIKey).filter(
                and_(
                    APIKey.user_id == user_id,
                    APIKey.exchange == exchange,
                    APIKey.is_active == True
                )
            ).first()
    
    # Strategy Management
    def create_strategy(self, user_id: int, name: str, type: str, 
                       config: Dict, symbols: List[str]) -> Strategy:
        """Create new trading strategy"""
        with self.get_session() as session:
            strategy = Strategy(
                user_id=user_id,
                name=name,
                type=type,
                config=config,
                symbols=symbols,
                is_active=False
            )
            session.add(strategy)
            session.flush()
            return strategy
    
    def get_active_strategies(self, user_id: int) -> List[Strategy]:
        """Get all active strategies for user"""
        with self.get_session() as session:
            return session.query(Strategy).filter(
                and_(Strategy.user_id == user_id, Strategy.is_active == True)
            ).all()
    
    def update_strategy_performance(self, strategy_id: int, metrics: Dict) -> bool:
        """Update strategy performance metrics"""
        with self.get_session() as session:
            strategy = session.query(Strategy).filter(Strategy.id == strategy_id).first()
            if strategy:
                strategy.performance = metrics
                strategy.updated_at = datetime.now(timezone.utc)
                return True
            return False
    
    # Trade Management
    def record_trade(self, user_id: int, trade_data: Dict) -> Trade:
        """Record a completed trade"""
        with self.get_session() as session:
            trade = Trade(
                user_id=user_id,
                strategy_id=trade_data.get('strategy_id'),
                symbol=trade_data['symbol'],
                side=OrderSide[trade_data['side'].upper()],
                entry_price=trade_data['entry_price'],
                exit_price=trade_data.get('exit_price'),
                quantity=trade_data['quantity'],
                entry_time=trade_data['entry_time'],
                exit_time=trade_data.get('exit_time'),
                pnl=trade_data.get('pnl', 0),
                pnl_percent=trade_data.get('pnl_percent', 0),
                fees=trade_data.get('fees', 0),
                is_paper=trade_data.get('is_paper', True),
                meta_data=trade_data.get('metadata', {})
            )
            session.add(trade)
            session.flush()
            return trade
    
    def get_trades(self, user_id: int, symbol: Optional[str] = None, 
                  start_date: Optional[datetime] = None, 
                  end_date: Optional[datetime] = None, 
                  limit: int = 100) -> List[Trade]:
        """Get trades with filters"""
        with self.get_session() as session:
            query = session.query(Trade).filter(Trade.user_id == user_id)
            
            if symbol:
                query = query.filter(Trade.symbol == symbol)
            if start_date:
                query = query.filter(Trade.entry_time >= start_date)
            if end_date:
                query = query.filter(Trade.entry_time <= end_date)
            
            return query.order_by(Trade.entry_time.desc()).limit(limit).all()
    
    # Position Management
    def create_position(self, user_id: int, position_data: Dict) -> Position:
        """Create new position"""
        with self.get_session() as session:
            position = Position(
                user_id=user_id,
                symbol=position_data['symbol'],
                side=OrderSide[position_data['side'].upper()],
                size=position_data['size'],
                entry_price=position_data['entry_price'],
                margin=position_data.get('margin', 0),
                leverage=position_data.get('leverage', 1),
                stop_loss=position_data.get('stop_loss'),
                take_profit=position_data.get('take_profit')
            )
            session.add(position)
            session.flush()
            return position
    
    def get_open_positions(self, user_id: int, symbol: Optional[str] = None) -> List[Position]:
        """Get open positions"""
        with self.get_session() as session:
            query = session.query(Position).filter(
                and_(Position.user_id == user_id, Position.status == PositionStatus.OPEN)
            )
            
            if symbol:
                query = query.filter(Position.symbol == symbol)
            
            return query.all()
    
    def update_position(self, position_id: int, updates: Dict) -> bool:
        """Update position data"""
        with self.get_session() as session:
            position = session.query(Position).filter(Position.id == position_id).first()
            if position:
                for key, value in updates.items():
                    if hasattr(position, key):
                        setattr(position, key, value)
                position.updated_at = datetime.now(timezone.utc)
                return True
            return False
    
    def close_position(self, position_id: int, exit_price: float, realized_pnl: float) -> bool:
        """Close a position"""
        with self.get_session() as session:
            position = session.query(Position).filter(Position.id == position_id).first()
            if position:
                position.status = PositionStatus.CLOSED
                position.realized_pnl = realized_pnl
                position.closed_at = datetime.now(timezone.utc)
                
                # Record as trade
                trade_data = {
                    'symbol': position.symbol,
                    'side': position.side.value,
                    'entry_price': position.entry_price,
                    'exit_price': exit_price,
                    'quantity': position.size,
                    'entry_time': position.created_at,
                    'exit_time': datetime.now(timezone.utc),
                    'pnl': realized_pnl,
                    'pnl_percent': (realized_pnl / (position.entry_price * position.size)) * 100
                }
                self.record_trade(position.user_id, trade_data)
                
                return True
            return False
    
    # Order Management
    def create_order(self, user_id: int, order_data: Dict) -> Order:
        """Create new order"""
        with self.get_session() as session:
            order = Order(
                user_id=user_id,
                position_id=order_data.get('position_id'),
                order_id=order_data['order_id'],
                symbol=order_data['symbol'],
                side=OrderSide[order_data['side'].upper()],
                type=OrderType[order_data['type'].upper()],
                price=order_data.get('price'),
                quantity=order_data['quantity'],
                time_in_force=order_data.get('time_in_force', 'GTC'),
                reduce_only=order_data.get('reduce_only', False),
                meta_data=order_data.get('metadata', {})
            )
            session.add(order)
            session.flush()
            return order
    
    def update_order_status(self, order_id: str, status: OrderStatus, 
                           filled_quantity: Optional[float] = None) -> bool:
        """Update order status"""
        with self.get_session() as session:
            order = session.query(Order).filter(Order.order_id == order_id).first()
            if order:
                order.status = status
                if filled_quantity:
                    order.filled_quantity = filled_quantity
                if status == OrderStatus.FILLED:
                    order.filled_at = datetime.now(timezone.utc)
                elif status == OrderStatus.CANCELLED:
                    order.cancelled_at = datetime.now(timezone.utc)
                return True
            return False
    
    # Market Data
    def save_market_data(self, data: List[Dict]) -> int:
        """Save market data (batch insert for efficiency)"""
        with self.get_session() as session:
            records = [
                MarketData(
                    symbol=d['symbol'],
                    timestamp=d['timestamp'],
                    open=d['open'],
                    high=d['high'],
                    low=d['low'],
                    close=d['close'],
                    volume=d['volume'],
                    timeframe=d['timeframe']
                ) for d in data
            ]
            session.bulk_save_objects(records)
            return len(records)
    
    def get_latest_market_data(self, symbol: str, timeframe: str = '1m', 
                              limit: int = 100) -> List[MarketData]:
        """Get latest market data"""
        with self.get_session() as session:
            return session.query(MarketData).filter(
                and_(MarketData.symbol == symbol, MarketData.timeframe == timeframe)
            ).order_by(MarketData.timestamp.desc()).limit(limit).all()
    
    # Signals
    def create_signal(self, strategy_id: int, signal_data: Dict) -> Signal:
        """Create trading signal"""
        with self.get_session() as session:
            signal = Signal(
                strategy_id=strategy_id,
                symbol=signal_data['symbol'],
                signal_type=signal_data['type'],
                strength=signal_data['strength'],
                price=signal_data['price'],
                meta_data=signal_data.get('metadata', {})
            )
            session.add(signal)
            session.flush()
            return signal
    
    def get_pending_signals(self, limit: int = 10) -> List[Signal]:
        """Get unexecuted signals"""
        with self.get_session() as session:
            return session.query(Signal).filter(
                Signal.executed == False
            ).order_by(Signal.created_at.desc()).limit(limit).all()
    
    def mark_signal_executed(self, signal_id: int) -> bool:
        """Mark signal as executed"""
        with self.get_session() as session:
            signal = session.query(Signal).filter(Signal.id == signal_id).first()
            if signal:
                signal.executed = True
                signal.executed_at = datetime.now(timezone.utc)
                return True
            return False
    
    # Alerts
    def create_alert(self, user_id: int, type: str, severity: str, 
                    title: str, message: str, metadata: Optional[Dict] = None, meta_data: Optional[Dict] = None) -> Alert:
        """Create user alert"""
        # Support both metadata and meta_data parameter names
        data = meta_data or metadata or {}
        with self.get_session() as session:
            alert = Alert(
                user_id=user_id,
                type=type,
                severity=severity,
                title=title,
                message=message,
                meta_data=data
            )
            session.add(alert)
            session.flush()
            return alert
    
    def get_unread_alerts(self, user_id: int) -> List[Alert]:
        """Get unread alerts for user"""
        with self.get_session() as session:
            return session.query(Alert).filter(
                and_(Alert.user_id == user_id, Alert.is_read == False)
            ).order_by(Alert.created_at.desc()).all()
    
    def mark_alerts_read(self, user_id: int, alert_ids: List[int]) -> int:
        """Mark alerts as read"""
        with self.get_session() as session:
            count = session.query(Alert).filter(
                and_(Alert.user_id == user_id, Alert.id.in_(alert_ids))
            ).update({'is_read': True, 'read_at': datetime.now(timezone.utc)})
            return count
    
    # System Logging
    def log_system_event(self, level: str, component: str, message: str, 
                        metadata: Optional[Dict] = None, meta_data: Optional[Dict] = None) -> SystemLog:
        """Log system event"""
        # Support both metadata and meta_data parameter names
        data = meta_data or metadata or {}
        with self.get_session() as session:
            log = SystemLog(
                level=level,
                component=component,
                message=message,
                meta_data=data
            )
            session.add(log)
            session.flush()
            return log
    
    def get_system_logs(self, component: Optional[str] = None, 
                       level: Optional[str] = None,
                       start_time: Optional[datetime] = None,
                       limit: int = 100) -> List[SystemLog]:
        """Get system logs with filters"""
        with self.get_session() as session:
            query = session.query(SystemLog)
            
            if component:
                query = query.filter(SystemLog.component == component)
            if level:
                query = query.filter(SystemLog.level == level)
            if start_time:
                query = query.filter(SystemLog.created_at >= start_time)
            
            return query.order_by(SystemLog.created_at.desc()).limit(limit).all()
    
    # Performance Tracking
    def save_daily_performance(self, user_id: int, metrics: Dict) -> Performance:
        """Save daily performance metrics"""
        with self.get_session() as session:
            # Check if record exists for today
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            
            perf = session.query(Performance).filter(
                and_(Performance.user_id == user_id, Performance.date == today)
            ).first()
            
            if perf:
                # Update existing record
                for key, value in metrics.items():
                    if hasattr(perf, key):
                        setattr(perf, key, value)
            else:
                # Create new record
                perf = Performance(
                    user_id=user_id,
                    date=today,
                    **metrics
                )
                session.add(perf)
            
            session.flush()
            return perf
    
    def get_performance_history(self, user_id: int, days: int = 30) -> List[Performance]:
        """Get performance history"""
        with self.get_session() as session:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)
            return session.query(Performance).filter(
                and_(Performance.user_id == user_id, Performance.date >= start_date)
            ).order_by(Performance.date).all()
    
    # Analytics Queries
    def get_trading_statistics(self, user_id: int, days: int = 30) -> Dict:
        """Get comprehensive trading statistics"""
        with self.get_session() as session:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Get trades
            trades = session.query(Trade).filter(
                and_(Trade.user_id == user_id, Trade.entry_time >= start_date)
            ).all()
            
            if not trades:
                return {
                    'total_trades': 0,
                    'win_rate': 0,
                    'total_pnl': 0,
                    'avg_pnl': 0,
                    'best_trade': 0,
                    'worst_trade': 0,
                    'avg_duration': 0
                }
            
            # Calculate statistics
            total_trades = len(trades)
            winning_trades = [t for t in trades if t.pnl > 0]
            losing_trades = [t for t in trades if t.pnl < 0]
            
            total_pnl = sum(t.pnl for t in trades)
            avg_pnl = total_pnl / total_trades
            best_trade = max(t.pnl for t in trades)
            worst_trade = min(t.pnl for t in trades)
            
            # Calculate average duration
            durations = []
            for t in trades:
                if t.exit_time:
                    duration = (t.exit_time - t.entry_time).total_seconds() / 3600  # hours
                    durations.append(duration)
            
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            return {
                'total_trades': total_trades,
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0,
                'total_pnl': total_pnl,
                'avg_pnl': avg_pnl,
                'best_trade': best_trade,
                'worst_trade': worst_trade,
                'avg_duration': avg_duration
            }
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> Dict[str, int]:
        """Clean up old data to save space"""
        with self.get_session() as session:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            # Clean up old market data
            market_data_deleted = session.query(MarketData).filter(
                MarketData.timestamp < cutoff_date
            ).delete()
            
            # Clean up old system logs
            logs_deleted = session.query(SystemLog).filter(
                SystemLog.created_at < cutoff_date
            ).delete()
            
            # Clean up old executed signals
            signals_deleted = session.query(Signal).filter(
                and_(Signal.created_at < cutoff_date, Signal.executed == True)
            ).delete()
            
            return {
                'market_data': market_data_deleted,
                'system_logs': logs_deleted,
                'signals': signals_deleted
            }

# Singleton instance
_db_service = None

def get_db_service() -> DatabaseService:
    """Get singleton database service instance"""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service

if __name__ == "__main__":
    # Test database connection
    db = get_db_service()
    logger.info("Database service ready!")
    
    # Example: Create test user
    try:
        from .models import UserRole
        user = db.create_user(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password_here",
            role=UserRole.TRADER
        )
        logger.info(f"Test user created: {user.username}")
    except Exception as e:
        logger.info(f"User might already exist: {e}")