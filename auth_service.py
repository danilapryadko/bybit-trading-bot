#!/usr/bin/env python3
"""
JWT Authentication Service
Provides secure authentication and authorization for the API
"""

import os
import jwt
import bcrypt
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List
from pydantic import BaseModel, EmailStr, Field
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Security
security = HTTPBearer()

# Pydantic models
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = Field("viewer", pattern="^(admin|trader|viewer)$")
    telegram_id: Optional[str] = None
    
class UserLogin(BaseModel):
    username: str
    password: str
    
class User(BaseModel):
    id: str
    username: str
    email: str
    role: str
    telegram_id: Optional[str]
    created_at: datetime
    last_login: Optional[datetime]
    is_active: bool = True
    
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    
class TokenData(BaseModel):
    username: str
    user_id: str
    role: str
    exp: datetime

class AuthService:
    def __init__(self):
        self.users_file = Path('users_db.json')
        self.users = self._load_users()
        self._ensure_admin_user()
        
    def _load_users(self) -> Dict[str, Dict]:
        """Load users from file"""
        if self.users_file.exists():
            with open(self.users_file, 'r') as f:
                return json.load(f)
        return {}
        
    def _save_users(self):
        """Save users to file"""
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f, indent=2, default=str)
            
    def _ensure_admin_user(self):
        """Create default admin user if doesn't exist"""
        if 'admin' not in self.users:
            admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
            self.create_user(
                username='admin',
                email='admin@bybit-bot.com',
                password=admin_password,
                role='admin'
            )
            logger.info("Default admin user created")
            
    def hash_password(self, password: str) -> str:
        """Hash a password"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
        
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against hash"""
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
        
    def create_user(self, username: str, email: str, password: str, role: str = 'viewer', telegram_id: str = None) -> User:
        """Create a new user"""
        if username in self.users:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
            
        user_id = f"user_{datetime.now().timestamp()}"
        user_data = {
            'id': user_id,
            'username': username,
            'email': email,
            'password_hash': self.hash_password(password),
            'role': role,
            'telegram_id': telegram_id,
            'created_at': datetime.now().isoformat(),
            'last_login': None,
            'is_active': True
        }
        
        self.users[username] = user_data
        self._save_users()
        
        return User(
            id=user_id,
            username=username,
            email=email,
            role=role,
            telegram_id=telegram_id,
            created_at=datetime.now(),
            last_login=None,
            is_active=True
        )
        
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user"""
        if username not in self.users:
            return None
            
        user_data = self.users[username]
        
        if not self.verify_password(password, user_data['password_hash']):
            return None
            
        if not user_data.get('is_active', True):
            return None
            
        # Update last login
        user_data['last_login'] = datetime.now().isoformat()
        self._save_users()
        
        return User(
            id=user_data['id'],
            username=user_data['username'],
            email=user_data['email'],
            role=user_data['role'],
            telegram_id=user_data.get('telegram_id'),
            created_at=datetime.fromisoformat(user_data['created_at']),
            last_login=datetime.now(),
            is_active=user_data['is_active']
        )
        
    def create_access_token(self, user: User) -> str:
        """Create JWT access token"""
        expires = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        payload = {
            'sub': user.username,
            'user_id': user.id,
            'role': user.role,
            'exp': expires,
            'iat': datetime.now(timezone.utc),
            'type': 'access'
        }
        
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        
    def create_refresh_token(self, user: User) -> str:
        """Create JWT refresh token"""
        expires = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        payload = {
            'sub': user.username,
            'user_id': user.id,
            'exp': expires,
            'iat': datetime.now(timezone.utc),
            'type': 'refresh'
        }
        
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        
    def verify_token(self, token: str) -> TokenData:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            username = payload.get('sub')
            user_id = payload.get('user_id')
            role = payload.get('role')
            exp = datetime.fromtimestamp(payload.get('exp'))
            
            if username is None or user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
                
            return TokenData(
                username=username,
                user_id=user_id,
                role=role,
                exp=exp
            )
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
            
    def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
        """Get current user from JWT token"""
        token = credentials.credentials
        token_data = self.verify_token(token)
        
        if token_data.username not in self.users:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
            
        user_data = self.users[token_data.username]
        
        return User(
            id=user_data['id'],
            username=user_data['username'],
            email=user_data['email'],
            role=user_data['role'],
            telegram_id=user_data.get('telegram_id'),
            created_at=datetime.fromisoformat(user_data['created_at']),
            last_login=datetime.fromisoformat(user_data['last_login']) if user_data.get('last_login') else None,
            is_active=user_data.get('is_active', True)
        )
        
    def refresh_access_token(self, refresh_token: str) -> Token:
        """Refresh access token using refresh token"""
        try:
            payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
            
            if payload.get('type') != 'refresh':
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )
                
            username = payload.get('sub')
            
            if username not in self.users:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
                
            user_data = self.users[username]
            
            user = User(
                id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                role=user_data['role'],
                telegram_id=user_data.get('telegram_id'),
                created_at=datetime.fromisoformat(user_data['created_at']),
                last_login=datetime.now(),
                is_active=user_data.get('is_active', True)
            )
            
            new_access_token = self.create_access_token(user)
            
            return Token(
                access_token=new_access_token,
                refresh_token=refresh_token,
                expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
            
    def check_permissions(self, user: User, required_role: str) -> bool:
        """Check if user has required role"""
        role_hierarchy = {
            'viewer': 0,
            'trader': 1,
            'admin': 2
        }
        
        user_level = role_hierarchy.get(user.role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level
        
    def require_role(self, role: str):
        """Dependency to require specific role"""
        def role_checker(current_user: User = Depends(self.get_current_user)):
            if not self.check_permissions(current_user, role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required role: {role}"
                )
            return current_user
        return role_checker
        
    def get_user_by_telegram_id(self, telegram_id: str) -> Optional[User]:
        """Get user by Telegram ID"""
        for username, user_data in self.users.items():
            if user_data.get('telegram_id') == telegram_id:
                return User(
                    id=user_data['id'],
                    username=user_data['username'],
                    email=user_data['email'],
                    role=user_data['role'],
                    telegram_id=user_data.get('telegram_id'),
                    created_at=datetime.fromisoformat(user_data['created_at']),
                    last_login=datetime.fromisoformat(user_data['last_login']) if user_data.get('last_login') else None,
                    is_active=user_data.get('is_active', True)
                )
        return None
        
    def update_user_role(self, username: str, new_role: str) -> User:
        """Update user role (admin only)"""
        if username not in self.users:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
            
        if new_role not in ['admin', 'trader', 'viewer']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role"
            )
            
        self.users[username]['role'] = new_role
        self._save_users()
        
        user_data = self.users[username]
        
        return User(
            id=user_data['id'],
            username=user_data['username'],
            email=user_data['email'],
            role=user_data['role'],
            telegram_id=user_data.get('telegram_id'),
            created_at=datetime.fromisoformat(user_data['created_at']),
            last_login=datetime.fromisoformat(user_data['last_login']) if user_data.get('last_login') else None,
            is_active=user_data.get('is_active', True)
        )
        
    def deactivate_user(self, username: str) -> bool:
        """Deactivate a user account"""
        if username not in self.users:
            return False
            
        self.users[username]['is_active'] = False
        self._save_users()
        return True
        
    def list_users(self) -> List[User]:
        """List all users (admin only)"""
        users = []
        
        for username, user_data in self.users.items():
            users.append(User(
                id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                role=user_data['role'],
                telegram_id=user_data.get('telegram_id'),
                created_at=datetime.fromisoformat(user_data['created_at']),
                last_login=datetime.fromisoformat(user_data['last_login']) if user_data.get('last_login') else None,
                is_active=user_data.get('is_active', True)
            ))
            
        return users


# Global instance
auth_service = AuthService()

# FastAPI dependencies
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current user dependency"""
    return auth_service.get_current_user(credentials)

def require_admin():
    """Require admin role dependency"""
    return auth_service.require_role('admin')

def require_trader():
    """Require trader role dependency"""
    return auth_service.require_role('trader')

def require_viewer():
    """Require viewer role dependency"""
    return auth_service.require_role('viewer')


# Example usage
if __name__ == "__main__":
    # Create auth service
    auth = AuthService()
    
    # Create a test user
    test_user = auth.create_user(
        username="testuser",
        email="test@example.com",
        password="testpassword123",
        role="trader"
    )
    print(f"Created user: {test_user.username}")
    
    # Authenticate user
    authenticated = auth.authenticate_user("testuser", "testpassword123")
    if authenticated:
        print(f"Authenticated: {authenticated.username}")
        
        # Create tokens
        access_token = auth.create_access_token(authenticated)
        refresh_token = auth.create_refresh_token(authenticated)
        
        print(f"Access token: {access_token[:50]}...")
        print(f"Refresh token: {refresh_token[:50]}...")
        
        # Verify token
        token_data = auth.verify_token(access_token)
        print(f"Token data: username={token_data.username}, role={token_data.role}")
        
        # Check permissions
        can_trade = auth.check_permissions(authenticated, 'trader')
        can_admin = auth.check_permissions(authenticated, 'admin')
        
        print(f"Can trade: {can_trade}")
        print(f"Can admin: {can_admin}")