#!/usr/bin/env python3
"""
Configuration management for Bybit Trading Bot
Handles testnet/mainnet switching and environment variables
"""

import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class TradingConfig:
    """Trading configuration"""
    # Environment
    is_testnet: bool
    
    # API Keys
    api_key: str
    api_secret: str
    
    # Bybit endpoints
    rest_url: str
    ws_url: str
    
    # Database
    database_url: str
    
    # Telegram
    telegram_token: str
    
    # Trading parameters (with defaults)
    default_leverage: int = 10
    max_position_size: float = 10000  # USD
    risk_per_trade: float = 0.02  # 2% risk per trade
    
    # Trading pairs
    trading_pairs: Optional[list] = None  # Will be loaded from trading_pairs_config
    
    # Optional fields
    telegram_chat_id: Optional[str] = None
    
    # System
    log_level: str = "INFO"
    debug_mode: bool = False

def get_config() -> TradingConfig:
    """Get current configuration based on environment"""
    
    # Check if we're in production mode
    use_mainnet = os.getenv('USE_MAINNET', 'false').lower() == 'true'
    
    if use_mainnet:
        # Mainnet configuration
        api_key = os.getenv('BYBIT_MAINNET_API_KEY', '')
        api_secret = os.getenv('BYBIT_MAINNET_API_SECRET', '')
        rest_url = "https://api.bybit.com"
        ws_url = "wss://stream.bybit.com"
        is_testnet = False
    else:
        # Testnet configuration (default)
        api_key = os.getenv('BYBIT_API_KEY', '')
        api_secret = os.getenv('BYBIT_API_SECRET', '')
        rest_url = "https://api-testnet.bybit.com"
        ws_url = "wss://stream-testnet.bybit.com"
        is_testnet = True
    
    # Database URL
    database_url = os.getenv('DATABASE_URL', 'postgresql://localhost/bybit_bot')
    
    # Handle Fly.io postgres:// vs postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    return TradingConfig(
        is_testnet=is_testnet,
        api_key=api_key,
        api_secret=api_secret,
        rest_url=rest_url,
        ws_url=ws_url,
        database_url=database_url,
        telegram_token=os.getenv('TELEGRAM_BOT_TOKEN', ''),
        telegram_chat_id=os.getenv('TELEGRAM_CHAT_ID'),
        default_leverage=int(os.getenv('DEFAULT_LEVERAGE', '10')),
        max_position_size=float(os.getenv('MAX_POSITION_SIZE', '10000')),
        risk_per_trade=float(os.getenv('RISK_PER_TRADE', '0.02')),
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        debug_mode=os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    )

# Singleton instance
_config: Optional[TradingConfig] = None

def get_trading_config() -> TradingConfig:
    """Get singleton trading configuration"""
    global _config
    if _config is None:
        _config = get_config()
    return _config

def reload_config():
    """Reload configuration (useful for switching between testnet/mainnet)"""
    global _config
    _config = get_config()
    return _config

def is_production() -> bool:
    """Check if running in production (mainnet) mode"""
    return get_trading_config().is_testnet == False

def is_testnet() -> bool:
    """Check if running in testnet mode"""
    return get_trading_config().is_testnet == True

if __name__ == "__main__":
    # Test configuration
    config = get_trading_config()
    print(f"Running in {'MAINNET' if not config.is_testnet else 'TESTNET'} mode")
    print(f"API Key present: {bool(config.api_key)}")
    print(f"Database URL: {config.database_url[:30]}...")
    print(f"Telegram Token present: {bool(config.telegram_token)}")
    print(f"Default Leverage: {config.default_leverage}x")
    print(f"Max Position Size: ${config.max_position_size}")
    print(f"Risk per Trade: {config.risk_per_trade * 100}%")