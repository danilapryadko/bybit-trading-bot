#!/usr/bin/env python3
"""
Configuration module tests
"""

import pytest
import os
from unittest.mock import patch
from config import (
    TradingConfig,
    get_config,
    get_trading_config,
    reload_config,
    is_production,
    is_testnet
)

class TestTradingConfig:
    """Test trading configuration"""
    
    def test_config_dataclass(self):
        """Test config dataclass structure"""
        config = TradingConfig(
            is_testnet=True,
            api_key="test_key",
            api_secret="test_secret",
            rest_url="https://api-testnet.bybit.com",
            ws_url="wss://stream-testnet.bybit.com",
            database_url="postgresql://localhost/test",
            telegram_token="test_token"
        )
        
        assert config.is_testnet == True
        assert config.api_key == "test_key"
        assert config.api_secret == "test_secret"
        assert config.default_leverage == 10
        assert config.max_position_size == 10000
        assert config.risk_per_trade == 0.02

class TestGetConfig:
    """Test configuration loading"""
    
    @patch.dict(os.environ, {
        'USE_MAINNET': 'false',
        'BYBIT_API_KEY': 'testnet_key',
        'BYBIT_API_SECRET': 'testnet_secret',
        'DATABASE_URL': 'postgresql://localhost/test',
        'TELEGRAM_BOT_TOKEN': 'test_token'
    })
    def test_testnet_config(self):
        """Test testnet configuration"""
        config = get_config()
        
        assert config.is_testnet == True
        assert config.api_key == 'testnet_key'
        assert config.api_secret == 'testnet_secret'
        assert config.rest_url == "https://api-testnet.bybit.com"
        assert config.ws_url == "wss://stream-testnet.bybit.com"
    
    @patch.dict(os.environ, {
        'USE_MAINNET': 'true',
        'BYBIT_MAINNET_API_KEY': 'mainnet_key',
        'BYBIT_MAINNET_API_SECRET': 'mainnet_secret',
        'DATABASE_URL': 'postgresql://localhost/test',
        'TELEGRAM_BOT_TOKEN': 'test_token'
    })
    def test_mainnet_config(self):
        """Test mainnet configuration"""
        config = get_config()
        
        assert config.is_testnet == False
        assert config.api_key == 'mainnet_key'
        assert config.api_secret == 'mainnet_secret'
        assert config.rest_url == "https://api.bybit.com"
        assert config.ws_url == "wss://stream.bybit.com"
    
    @patch.dict(os.environ, {
        'DATABASE_URL': 'postgres://user:pass@host/db',
        'DEFAULT_LEVERAGE': '20',
        'MAX_POSITION_SIZE': '50000',
        'RISK_PER_TRADE': '0.05',
        'LOG_LEVEL': 'DEBUG',
        'DEBUG_MODE': 'true'
    })
    def test_custom_settings(self):
        """Test custom settings from environment"""
        config = get_config()
        
        # Should convert postgres:// to postgresql://
        assert config.database_url.startswith('postgresql://')
        assert config.default_leverage == 20
        assert config.max_position_size == 50000
        assert config.risk_per_trade == 0.05
        assert config.log_level == 'DEBUG'
        assert config.debug_mode == True
    
    @patch.dict(os.environ, {
        'TELEGRAM_CHAT_ID': '123456789'
    })
    def test_optional_settings(self):
        """Test optional settings"""
        config = get_config()
        
        assert config.telegram_chat_id == '123456789'

class TestConfigSingleton:
    """Test configuration singleton"""
    
    @patch.dict(os.environ, {'USE_MAINNET': 'false'})
    def test_singleton(self):
        """Test singleton pattern"""
        config1 = get_trading_config()
        config2 = get_trading_config()
        
        assert config1 is config2
    
    @patch.dict(os.environ, {'USE_MAINNET': 'false'})
    def test_reload_config(self):
        """Test configuration reload"""
        config1 = get_trading_config()
        
        # Change environment
        with patch.dict(os.environ, {'USE_MAINNET': 'true'}):
            config2 = reload_config()
            
            assert config2.is_testnet == False
            assert config2 is get_trading_config()

class TestHelperFunctions:
    """Test helper functions"""
    
    @patch.dict(os.environ, {'USE_MAINNET': 'true'})
    def test_is_production(self):
        """Test production check"""
        reload_config()
        assert is_production() == True
        assert is_testnet() == False
    
    @patch.dict(os.environ, {'USE_MAINNET': 'false'})
    def test_is_testnet(self):
        """Test testnet check"""
        reload_config()
        assert is_production() == False
        assert is_testnet() == True

class TestConfigDefaults:
    """Test configuration defaults"""
    
    @patch.dict(os.environ, {}, clear=True)
    def test_all_defaults(self):
        """Test all default values"""
        config = get_config()
        
        # Should use testnet by default
        assert config.is_testnet == True
        
        # Should have empty API keys
        assert config.api_key == ''
        assert config.api_secret == ''
        
        # Should have default database URL
        assert 'localhost' in config.database_url
        
        # Should have default trading parameters
        assert config.default_leverage == 10
        assert config.max_position_size == 10000
        assert config.risk_per_trade == 0.02
        
        # Should have default system settings
        assert config.log_level == 'INFO'
        assert config.debug_mode == False

@pytest.fixture
def clean_config():
    """Fixture to clean config singleton"""
    import config
    config._config = None
    yield
    config._config = None

def test_config_isolation(clean_config):
    """Test config isolation between tests"""
    with patch.dict(os.environ, {'USE_MAINNET': 'true'}):
        config1 = get_trading_config()
        assert config1.is_testnet == False
    
    # Reset singleton
    import config
    config._config = None
    
    with patch.dict(os.environ, {'USE_MAINNET': 'false'}):
        config2 = get_trading_config()
        assert config2.is_testnet == True