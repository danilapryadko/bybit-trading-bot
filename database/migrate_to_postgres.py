#!/usr/bin/env python3
"""
Migration script to move data from JSON files to PostgreSQL
One-time migration for production deployment
"""

import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
import bcrypt

# Add parent directory to path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from database.service import get_db_service
from database.models import UserRole

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataMigration:
    """Migrate data from JSON to PostgreSQL"""
    
    def __init__(self):
        self.db = get_db_service()
        self.base_dir = Path(__file__).parent.parent
        logger.info("Data migration initialized")
    
    def migrate_users(self):
        """Migrate users from users_db.json"""
        users_file = self.base_dir / "users_db.json"
        
        if not users_file.exists():
            logger.info("No users_db.json found, creating default admin user")
            # Create default admin user
            admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
            hashed = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            user = self.db.create_user(
                username='admin',
                email='admin@bybit-bot.com',
                password_hash=hashed,
                role=UserRole.ADMIN
            )
            logger.info(f"Created admin user: {user.username}")
            
            # Create your personal user
            your_password = os.getenv('USER_PASSWORD', 'secure_password_123')
            your_hashed = bcrypt.hashpw(your_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            your_user = self.db.create_user(
                username='danila',
                email='danilapryadko@icloud.com',
                password_hash=your_hashed,
                role=UserRole.ADMIN,
                telegram_id='384403397'
            )
            logger.info(f"Created your user: {your_user.username}")
            return
        
        # Load existing users
        with open(users_file, 'r') as f:
            users_data = json.load(f)
        
        migrated = 0
        for username, user_data in users_data.items():
            try:
                # Check if user already exists
                existing = self.db.get_user(username=username)
                if existing:
                    logger.info(f"User {username} already exists, skipping")
                    continue
                
                # Create user
                role = UserRole[user_data.get('role', 'viewer').upper()]
                user = self.db.create_user(
                    username=username,
                    email=user_data.get('email', f'{username}@bybit-bot.com'),
                    password_hash=user_data.get('password_hash', ''),
                    role=role,
                    telegram_id=user_data.get('telegram_id')
                )
                
                # Update settings if any
                if 'settings' in user_data:
                    self.db.update_user_settings(user.id, user_data['settings'])
                
                migrated += 1
                logger.info(f"Migrated user: {username}")
                
            except Exception as e:
                logger.error(f"Error migrating user {username}: {e}")
        
        logger.info(f"Migrated {migrated} users")
    
    def migrate_api_keys(self):
        """Migrate API keys from environment variables"""
        # Get Bybit API keys from environment
        testnet_key = os.getenv('BYBIT_API_KEY')
        testnet_secret = os.getenv('BYBIT_API_SECRET')
        mainnet_key = os.getenv('BYBIT_MAINNET_API_KEY')
        mainnet_secret = os.getenv('BYBIT_MAINNET_API_SECRET')
        
        # Get admin user
        admin = self.db.get_user(username='admin')
        if not admin:
            logger.error("Admin user not found")
            return
        
        # Save testnet keys
        if testnet_key and testnet_secret:
            try:
                self.db.save_api_keys(
                    user_id=admin.id,
                    api_key=testnet_key,
                    api_secret=testnet_secret,
                    exchange='bybit',
                    is_testnet=True
                )
                logger.info("Migrated testnet API keys")
            except Exception as e:
                logger.error(f"Error saving testnet keys: {e}")
        
        # Save mainnet keys
        if mainnet_key and mainnet_secret:
            try:
                self.db.save_api_keys(
                    user_id=admin.id,
                    api_key=mainnet_key,
                    api_secret=mainnet_secret,
                    exchange='bybit',
                    is_testnet=False
                )
                logger.info("Migrated mainnet API keys")
            except Exception as e:
                logger.error(f"Error saving mainnet keys: {e}")
    
    def migrate_strategies(self):
        """Create default strategies"""
        # Get admin user
        admin = self.db.get_user(username='admin')
        if not admin:
            logger.error("Admin user not found")
            return
        
        # Default strategies
        strategies = [
            {
                'name': 'RSI Strategy',
                'type': 'technical',
                'config': {
                    'period': 14,
                    'oversold': 30,
                    'overbought': 70,
                    'timeframe': '15m'
                },
                'symbols': ['BTCUSDT', 'ETHUSDT']
            },
            {
                'name': 'EMA Crossover',
                'type': 'technical',
                'config': {
                    'short_period': 9,
                    'long_period': 21,
                    'timeframe': '1h'
                },
                'symbols': ['BTCUSDT', 'ETHUSDT']
            },
            {
                'name': 'ML Ensemble',
                'type': 'ml',
                'config': {
                    'models': ['lstm', 'random_forest', 'xgboost'],
                    'lookback': 100,
                    'features': 50,
                    'retrain_days': 7
                },
                'symbols': ['BTCUSDT']
            },
            {
                'name': 'Scalping Bot',
                'type': 'hybrid',
                'config': {
                    'min_spread': 0.01,
                    'volume_threshold': 1000000,
                    'hold_time': 300,  # 5 minutes
                    'stop_loss': 0.5,
                    'take_profit': 1.0
                },
                'symbols': ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
            }
        ]
        
        for strategy_data in strategies:
            try:
                strategy = self.db.create_strategy(
                    user_id=admin.id,
                    name=strategy_data['name'],
                    type=strategy_data['type'],
                    config=strategy_data['config'],
                    symbols=strategy_data['symbols']
                )
                logger.info(f"Created strategy: {strategy.name}")
            except Exception as e:
                logger.error(f"Error creating strategy {strategy_data['name']}: {e}")
    
    def migrate_report_settings(self):
        """Migrate report settings from user_report_settings.json"""
        settings_file = self.base_dir / "user_report_settings.json"
        
        if not settings_file.exists():
            logger.info("No user_report_settings.json found")
            return
        
        with open(settings_file, 'r') as f:
            settings_data = json.load(f)
        
        for telegram_id, settings in settings_data.items():
            try:
                # Find user by telegram ID
                user = self.db.get_user(telegram_id=telegram_id)
                if not user:
                    logger.warning(f"No user found for telegram_id: {telegram_id}")
                    continue
                
                # Update user settings
                user_settings = {
                    'reports': settings,
                    'notifications': {
                        'telegram': True,
                        'email': False
                    }
                }
                self.db.update_user_settings(user.id, user_settings)
                logger.info(f"Migrated settings for user: {user.username}")
                
            except Exception as e:
                logger.error(f"Error migrating settings for {telegram_id}: {e}")
    
    def create_sample_data(self):
        """Create sample trades and positions for testing"""
        # Get admin user
        admin = self.db.get_user(username='admin')
        if not admin:
            logger.error("Admin user not found")
            return
        
        # Check if we already have trades
        existing_trades = self.db.get_trades(admin.id, limit=1)
        if existing_trades:
            logger.info("Sample data already exists")
            return
        
        # Create sample trades
        sample_trades = [
            {
                'symbol': 'BTCUSDT',
                'side': 'buy',
                'entry_price': 64000,
                'exit_price': 65000,
                'quantity': 0.01,
                'entry_time': datetime.now(timezone.utc),
                'exit_time': datetime.now(timezone.utc),
                'pnl': 10.0,
                'pnl_percent': 1.56,
                'fees': 0.5,
                'is_paper': True
            },
            {
                'symbol': 'ETHUSDT',
                'side': 'sell',
                'entry_price': 3200,
                'exit_price': 3150,
                'quantity': 0.1,
                'entry_time': datetime.now(timezone.utc),
                'exit_time': datetime.now(timezone.utc),
                'pnl': 5.0,
                'pnl_percent': 1.56,
                'fees': 0.3,
                'is_paper': True
            }
        ]
        
        for trade_data in sample_trades:
            try:
                trade = self.db.record_trade(admin.id, trade_data)
                logger.info(f"Created sample trade: {trade.symbol} P&L: ${trade.pnl}")
            except Exception as e:
                logger.error(f"Error creating sample trade: {e}")
        
        # Create sample position
        try:
            position = self.db.create_position(admin.id, {
                'symbol': 'BTCUSDT',
                'side': 'buy',
                'size': 0.01,
                'entry_price': 65000,
                'margin': 650,
                'leverage': 10,
                'stop_loss': 63700,
                'take_profit': 66300
            })
            logger.info(f"Created sample position: {position.symbol}")
        except Exception as e:
            logger.error(f"Error creating sample position: {e}")
        
        # Create sample alert
        try:
            alert = self.db.create_alert(
                user_id=admin.id,
                type='system',
                severity='info',
                title='Database Migration Complete',
                message='Your data has been successfully migrated to PostgreSQL',
                meta_data={'migration_date': datetime.now(timezone.utc).isoformat()}
            )
            logger.info("Created welcome alert")
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
    
    def run_migration(self):
        """Run full migration"""
        logger.info("Starting data migration to PostgreSQL...")
        
        try:
            # Step 1: Migrate users
            logger.info("Step 1: Migrating users...")
            self.migrate_users()
            
            # Step 2: Migrate API keys
            logger.info("Step 2: Migrating API keys...")
            self.migrate_api_keys()
            
            # Step 3: Create strategies
            logger.info("Step 3: Creating strategies...")
            self.migrate_strategies()
            
            # Step 4: Migrate report settings
            logger.info("Step 4: Migrating report settings...")
            self.migrate_report_settings()
            
            # Step 5: Create sample data
            logger.info("Step 5: Creating sample data...")
            self.create_sample_data()
            
            logger.info("✅ Migration completed successfully!")
            
            # Log migration event
            self.db.log_system_event(
                level='info',
                component='migration',
                message='Database migration completed successfully',
                meta_data={
                    'migration_date': datetime.now(timezone.utc).isoformat(),
                    'version': '2.0.0'
                }
            )
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise

if __name__ == "__main__":
    migration = DataMigration()
    migration.run_migration()