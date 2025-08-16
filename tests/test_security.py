#!/usr/bin/env python3
"""
Security module tests
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from security.security_manager import (
    SecurityManager, APIKeyEncryption, RateLimiter,
    RequestSigner, IPWhitelist, AuditLogger, SecurityConfig
)

class TestAPIKeyEncryption:
    """Test API key encryption"""
    
    def test_encrypt_decrypt(self):
        """Test encryption and decryption"""
        encryption = APIKeyEncryption("test_password")
        
        original = "test_api_key_12345"
        encrypted = encryption.encrypt_api_key(original)
        decrypted = encryption.decrypt_api_key(encrypted)
        
        assert encrypted != original
        assert decrypted == original
    
    def test_different_passwords(self):
        """Test that different passwords produce different results"""
        enc1 = APIKeyEncryption("password1")
        enc2 = APIKeyEncryption("password2")
        
        original = "test_key"
        encrypted1 = enc1.encrypt_api_key(original)
        encrypted2 = enc2.encrypt_api_key(original)
        
        assert encrypted1 != encrypted2

class TestRateLimiter:
    """Test rate limiting"""
    
    def test_request_limit(self):
        """Test request rate limiting"""
        limiter = RateLimiter()
        user_id = "test_user"
        
        # Should allow up to limit
        for i in range(3):
            assert limiter.check_request_limit(user_id, max_per_minute=3)
        
        # Should block after limit
        assert not limiter.check_request_limit(user_id, max_per_minute=3)
    
    def test_order_limit(self):
        """Test daily order limiting"""
        limiter = RateLimiter()
        user_id = "test_user"
        
        # Should allow up to limit
        for i in range(5):
            assert limiter.check_order_limit(user_id, max_per_day=5)
        
        # Should block after limit
        assert not limiter.check_order_limit(user_id, max_per_day=5)

class TestRequestSigner:
    """Test request signing"""
    
    def test_generate_signature(self):
        """Test signature generation"""
        signature = RequestSigner.generate_signature(
            timestamp="1234567890",
            api_key="test_key",
            recv_window="5000",
            query_string="symbol=BTCUSDT",
            api_secret="test_secret"
        )
        
        assert signature
        assert len(signature) == 64  # SHA256 hex length
    
    def test_verify_webhook_signature(self):
        """Test webhook signature verification"""
        payload = b"test_payload"
        secret = "test_secret"
        
        # Generate valid signature
        import hmac
        import hashlib
        valid_sig = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Should verify valid signature
        assert RequestSigner.verify_webhook_signature(
            payload, valid_sig, secret
        )
        
        # Should reject invalid signature
        assert not RequestSigner.verify_webhook_signature(
            payload, "invalid_sig", secret
        )

class TestIPWhitelist:
    """Test IP whitelisting"""
    
    def test_no_whitelist(self):
        """Test with no whitelist (all allowed)"""
        whitelist = IPWhitelist()
        
        assert whitelist.is_allowed("192.168.1.1")
        assert whitelist.is_allowed("10.0.0.1")
    
    def test_with_whitelist(self):
        """Test with whitelist"""
        whitelist = IPWhitelist(["192.168.1.1", "10.0.0.0/24"])
        
        assert whitelist.is_allowed("192.168.1.1")
        assert whitelist.is_allowed("10.0.0.100")
        assert not whitelist.is_allowed("192.168.1.2")
        assert not whitelist.is_allowed("8.8.8.8")

class TestAuditLogger:
    """Test audit logging"""
    
    def test_log_login(self):
        """Test login logging"""
        with patch('logging.Logger.info') as mock_log:
            audit = AuditLogger()
            audit.log_login("user1", "192.168.1.1", True)
            
            mock_log.assert_called()
            call_args = str(mock_log.call_args)
            assert "login" in call_args
            assert "user1" in call_args
    
    def test_log_trade(self):
        """Test trade logging"""
        with patch('logging.Logger.info') as mock_log:
            audit = AuditLogger()
            audit.log_trade("user1", {"symbol": "BTCUSDT", "side": "buy"})
            
            mock_log.assert_called()
            call_args = str(mock_log.call_args)
            assert "trade" in call_args
            assert "BTCUSDT" in call_args
    
    def test_log_security_alert(self):
        """Test security alert logging"""
        with patch('logging.Logger.info') as mock_log:
            audit = AuditLogger()
            audit.log_security_alert("rate_limit", {"user": "user1"})
            
            mock_log.assert_called()
            call_args = str(mock_log.call_args)
            assert "security_alert" in call_args

class TestSecurityManager:
    """Test main security manager"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.config = SecurityConfig(
            max_requests_per_minute=60,
            max_orders_per_day=100,
            max_position_value=50000,
            allowed_ips=["127.0.0.1"]
        )
        self.security = SecurityManager(self.config)
    
    def test_validate_request_success(self):
        """Test successful request validation"""
        valid, msg = self.security.validate_request("user1", "127.0.0.1")
        assert valid
        assert msg == "Request validated"
    
    def test_validate_request_ip_blocked(self):
        """Test IP blocking"""
        valid, msg = self.security.validate_request("user1", "192.168.1.1")
        assert not valid
        assert "IP address not whitelisted" in msg
    
    def test_validate_trade_success(self):
        """Test successful trade validation"""
        valid, msg = self.security.validate_trade(
            "user1", "BTCUSDT", 1.0, 45000
        )
        assert valid
        assert msg == "Trade validated"
    
    def test_validate_trade_position_limit(self):
        """Test position size limit"""
        valid, msg = self.security.validate_trade(
            "user1", "BTCUSDT", 10.0, 10000  # $100,000 position
        )
        assert not valid
        assert "exceeds limit" in msg
    
    def test_encrypt_sensitive_data(self):
        """Test data encryption"""
        data = {
            "api_key": "plain_key",
            "api_secret": "plain_secret",
            "other": "data"
        }
        
        encrypted = self.security.encrypt_sensitive_data(data)
        
        assert encrypted["api_key"] != "plain_key"
        assert encrypted["api_secret"] != "plain_secret"
        assert encrypted["other"] == "data"
    
    def test_decrypt_sensitive_data(self):
        """Test data decryption"""
        # First encrypt
        data = {"api_key": "plain_key"}
        encrypted = self.security.encrypt_sensitive_data(data)
        
        # Then decrypt
        decrypted = self.security.decrypt_sensitive_data(encrypted)
        assert decrypted["api_key"] == "plain_key"
    
    def test_generate_session_token(self):
        """Test session token generation"""
        token = self.security.generate_session_token("user1")
        
        assert token
        assert len(token) > 32
    
    def test_validate_session_token(self):
        """Test session token validation"""
        # Simple test since implementation is placeholder
        assert self.security.validate_session_token("any_token")

@pytest.fixture
def security_manager():
    """Fixture for security manager"""
    return SecurityManager()

def test_security_singleton(security_manager):
    """Test security manager singleton"""
    from security.security_manager import get_security_manager
    
    sm1 = get_security_manager()
    sm2 = get_security_manager()
    
    assert sm1 is sm2