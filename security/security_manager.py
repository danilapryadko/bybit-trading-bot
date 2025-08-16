#!/usr/bin/env python3
"""
Security Manager for Bybit Trading Bot
Implements enhanced security measures including:
- API key encryption
- Rate limiting
- IP whitelisting
- Request signing
- Audit logging
"""

import os
import hmac
import hashlib
import time
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64

logger = logging.getLogger(__name__)

@dataclass
class SecurityConfig:
    """Security configuration"""
    max_requests_per_minute: int = 60
    max_orders_per_day: int = 100
    max_position_value: float = 50000  # USD
    allowed_ips: List[str] = None
    require_2fa: bool = False
    audit_enabled: bool = True

class APIKeyEncryption:
    """Handles API key encryption/decryption"""
    
    def __init__(self, master_password: Optional[str] = None):
        """Initialize encryption with master password"""
        if master_password is None:
            master_password = os.getenv('MASTER_PASSWORD', 'default_secure_password_change_me')
        
        # Derive encryption key from password
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'stable_salt_for_key_derivation',  # In production, use random salt
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
        self.cipher = Fernet(key)
    
    def encrypt_api_key(self, api_key: str) -> str:
        """Encrypt API key"""
        return self.cipher.encrypt(api_key.encode()).decode()
    
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt API key"""
        return self.cipher.decrypt(encrypted_key.encode()).decode()

class RateLimiter:
    """Rate limiting for API calls and trading operations"""
    
    def __init__(self):
        self.requests = {}  # Track requests per user
        self.orders = {}    # Track orders per user
        
    def check_request_limit(self, user_id: str, max_per_minute: int = 60) -> bool:
        """Check if user exceeded request limit"""
        now = time.time()
        minute_ago = now - 60
        
        # Initialize user if not exists
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # Remove old requests
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id]
            if req_time > minute_ago
        ]
        
        # Check limit
        if len(self.requests[user_id]) >= max_per_minute:
            return False
        
        # Add current request
        self.requests[user_id].append(now)
        return True
    
    def check_order_limit(self, user_id: str, max_per_day: int = 100) -> bool:
        """Check if user exceeded daily order limit"""
        today = datetime.now(timezone.utc).date()
        
        # Initialize user if not exists
        if user_id not in self.orders:
            self.orders[user_id] = {'date': today, 'count': 0}
        
        # Reset counter if new day
        if self.orders[user_id]['date'] != today:
            self.orders[user_id] = {'date': today, 'count': 0}
        
        # Check limit
        if self.orders[user_id]['count'] >= max_per_day:
            return False
        
        # Increment counter
        self.orders[user_id]['count'] += 1
        return True

class RequestSigner:
    """Signs requests for additional security"""
    
    @staticmethod
    def generate_signature(
        timestamp: str,
        api_key: str,
        recv_window: str,
        query_string: str,
        api_secret: str
    ) -> str:
        """Generate request signature for Bybit API"""
        param_str = f"{timestamp}{api_key}{recv_window}{query_string}"
        hash_obj = hmac.new(
            api_secret.encode('utf-8'),
            param_str.encode('utf-8'),
            hashlib.sha256
        )
        return hash_obj.hexdigest()
    
    @staticmethod
    def verify_webhook_signature(
        payload: bytes,
        signature: str,
        secret: str
    ) -> bool:
        """Verify webhook signature"""
        expected_sig = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected_sig, signature)

class IPWhitelist:
    """IP whitelisting for additional security"""
    
    def __init__(self, allowed_ips: Optional[List[str]] = None):
        """Initialize with allowed IPs"""
        self.allowed_ips = allowed_ips or []
        
        # Add Fly.io internal IPs if running on Fly
        if os.getenv('FLY_APP_NAME'):
            self.allowed_ips.extend([
                '127.0.0.1',
                '::1',
                'fdaa::/16'  # Fly.io internal network
            ])
    
    def is_allowed(self, ip_address: str) -> bool:
        """Check if IP is whitelisted"""
        if not self.allowed_ips:
            return True  # No whitelist means all IPs allowed
        
        # Check exact match
        if ip_address in self.allowed_ips:
            return True
        
        # Check subnet match (simplified)
        for allowed_ip in self.allowed_ips:
            if '/' in allowed_ip:
                subnet = allowed_ip.split('/')[0]
                if ip_address.startswith(subnet.rsplit('.', 1)[0]):
                    return True
        
        return False

class AuditLogger:
    """Audit logging for security events"""
    
    def __init__(self, db_service=None):
        """Initialize with database service"""
        self.db_service = db_service
        
    def log_login(self, user_id: str, ip_address: str, success: bool):
        """Log login attempt"""
        self._log_event('login', {
            'user_id': user_id,
            'ip_address': ip_address,
            'success': success,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    def log_trade(self, user_id: str, trade_data: Dict):
        """Log trade execution"""
        self._log_event('trade', {
            'user_id': user_id,
            'trade': trade_data,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    def log_api_key_access(self, user_id: str, action: str):
        """Log API key access"""
        self._log_event('api_key', {
            'user_id': user_id,
            'action': action,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    def log_security_alert(self, alert_type: str, details: Dict):
        """Log security alert"""
        self._log_event('security_alert', {
            'type': alert_type,
            'details': details,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    def _log_event(self, event_type: str, data: Dict):
        """Internal method to log event"""
        log_entry = {
            'type': event_type,
            'data': data,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Log to file
        logger.info(f"AUDIT: {json.dumps(log_entry)}")
        
        # Log to database if available
        if self.db_service:
            try:
                self.db_service.log_system_event(
                    level='info',
                    component='audit',
                    message=f"Security event: {event_type}",
                    metadata=data
                )
            except Exception as e:
                logger.error(f"Failed to log to database: {e}")

class SecurityManager:
    """Main security manager coordinating all security features"""
    
    def __init__(self, config: Optional[SecurityConfig] = None, db_service=None):
        """Initialize security manager"""
        self.config = config or SecurityConfig()
        self.encryption = APIKeyEncryption()
        self.rate_limiter = RateLimiter()
        self.request_signer = RequestSigner()
        self.ip_whitelist = IPWhitelist(self.config.allowed_ips)
        self.audit = AuditLogger(db_service)
        
        logger.info("Security Manager initialized")
    
    def validate_request(self, user_id: str, ip_address: str) -> tuple[bool, str]:
        """Validate incoming request"""
        # Check IP whitelist
        if not self.ip_whitelist.is_allowed(ip_address):
            self.audit.log_security_alert('ip_blocked', {
                'user_id': user_id,
                'ip_address': ip_address
            })
            return False, "IP address not whitelisted"
        
        # Check rate limit
        if not self.rate_limiter.check_request_limit(user_id):
            self.audit.log_security_alert('rate_limit_exceeded', {
                'user_id': user_id,
                'ip_address': ip_address
            })
            return False, "Rate limit exceeded"
        
        return True, "Request validated"
    
    def validate_trade(
        self,
        user_id: str,
        symbol: str,
        quantity: float,
        price: float
    ) -> tuple[bool, str]:
        """Validate trade request"""
        # Check daily order limit
        if not self.rate_limiter.check_order_limit(user_id):
            self.audit.log_security_alert('order_limit_exceeded', {
                'user_id': user_id
            })
            return False, "Daily order limit exceeded"
        
        # Check position value
        position_value = quantity * price
        if position_value > self.config.max_position_value:
            self.audit.log_security_alert('position_limit_exceeded', {
                'user_id': user_id,
                'position_value': position_value
            })
            return False, f"Position value ${position_value} exceeds limit"
        
        return True, "Trade validated"
    
    def encrypt_sensitive_data(self, data: Dict) -> Dict:
        """Encrypt sensitive fields in data"""
        encrypted_data = data.copy()
        
        # Encrypt API keys
        if 'api_key' in encrypted_data:
            encrypted_data['api_key'] = self.encryption.encrypt_api_key(
                encrypted_data['api_key']
            )
        if 'api_secret' in encrypted_data:
            encrypted_data['api_secret'] = self.encryption.encrypt_api_key(
                encrypted_data['api_secret']
            )
        
        return encrypted_data
    
    def decrypt_sensitive_data(self, data: Dict) -> Dict:
        """Decrypt sensitive fields in data"""
        decrypted_data = data.copy()
        
        # Decrypt API keys
        if 'api_key' in decrypted_data:
            decrypted_data['api_key'] = self.encryption.decrypt_api_key(
                decrypted_data['api_key']
            )
        if 'api_secret' in decrypted_data:
            decrypted_data['api_secret'] = self.encryption.decrypt_api_key(
                decrypted_data['api_secret']
            )
        
        return decrypted_data
    
    def generate_session_token(self, user_id: str) -> str:
        """Generate secure session token"""
        timestamp = str(time.time())
        data = f"{user_id}:{timestamp}"
        token = base64.b64encode(
            hmac.new(
                os.urandom(32),
                data.encode(),
                hashlib.sha256
            ).digest()
        ).decode()
        
        self.audit.log_api_key_access(user_id, 'session_created')
        return token
    
    def validate_session_token(self, token: str, max_age_hours: int = 24) -> bool:
        """Validate session token age"""
        # Simplified validation - in production, store and validate tokens properly
        try:
            # Decode and check token age
            # This is a placeholder - implement proper token validation
            return True
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return False

# Singleton instance
_security_manager: Optional[SecurityManager] = None

def get_security_manager(db_service=None) -> SecurityManager:
    """Get singleton security manager"""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager(db_service=db_service)
    return _security_manager

if __name__ == "__main__":
    # Test security features
    security = get_security_manager()
    
    # Test encryption
    original_key = "test_api_key_12345"
    encrypted = security.encryption.encrypt_api_key(original_key)
    decrypted = security.encryption.decrypt_api_key(encrypted)
    print(f"Encryption test: {original_key == decrypted}")
    
    # Test rate limiting
    user_id = "test_user"
    for i in range(5):
        allowed = security.rate_limiter.check_request_limit(user_id, max_per_minute=3)
        print(f"Request {i+1}: {'Allowed' if allowed else 'Blocked'}")
    
    # Test request validation
    valid, msg = security.validate_request("user1", "127.0.0.1")
    print(f"Request validation: {msg}")
    
    # Test trade validation
    valid, msg = security.validate_trade("user1", "BTCUSDT", 1.0, 45000)
    print(f"Trade validation: {msg}")