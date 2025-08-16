#!/usr/bin/env python3
"""
Rate Limiting Middleware for API Protection
"""

import time
import logging
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import redis
import json
import hashlib

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter implementation with multiple strategies"""
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        requests_per_day: int = 10000,
        use_redis: bool = False,
        redis_url: Optional[str] = None,
        enable_sliding_window: bool = True,
        enable_token_bucket: bool = False,
        burst_size: int = 10
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day
        self.enable_sliding_window = enable_sliding_window
        self.enable_token_bucket = enable_token_bucket
        self.burst_size = burst_size
        
        # Redis for distributed rate limiting
        self.redis_client = None
        if use_redis and redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
                logger.info("Redis connected for distributed rate limiting")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}, using in-memory rate limiting")
        
        # In-memory storage for rate limiting
        self.request_history = defaultdict(lambda: deque(maxlen=10000))
        self.token_buckets = defaultdict(lambda: {
            'tokens': burst_size,
            'last_refill': time.time()
        })
        
        # IP-based blocking
        self.blocked_ips = set()
        self.suspicious_ips = defaultdict(int)
        
    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier"""
        # Try to get authenticated user ID first
        user_id = getattr(request.state, 'user_id', None)
        if user_id:
            return f"user:{user_id}"
        
        # Fall back to IP address
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            client_ip = forwarded_for.split(',')[0].strip()
        else:
            client_ip = request.client.host
            
        return f"ip:{client_ip}"
    
    def _get_endpoint_key(self, request: Request) -> str:
        """Get endpoint-specific rate limit key"""
        path = request.url.path
        method = request.method
        return hashlib.md5(f"{method}:{path}".encode()).hexdigest()
    
    async def check_rate_limit(self, request: Request) -> Tuple[bool, Optional[Dict]]:
        """Check if request exceeds rate limit"""
        client_id = self._get_client_id(request)
        endpoint_key = self._get_endpoint_key(request)
        
        # Check if IP is blocked
        if client_id.startswith("ip:") and client_id[3:] in self.blocked_ips:
            return False, {"error": "IP blocked due to excessive requests"}
        
        # Use Redis if available
        if self.redis_client:
            return await self._check_redis_rate_limit(client_id, endpoint_key)
        
        # Use in-memory rate limiting
        if self.enable_sliding_window:
            return self._check_sliding_window(client_id)
        elif self.enable_token_bucket:
            return self._check_token_bucket(client_id)
        else:
            return self._check_fixed_window(client_id)
    
    async def _check_redis_rate_limit(
        self,
        client_id: str,
        endpoint_key: str
    ) -> Tuple[bool, Optional[Dict]]:
        """Check rate limit using Redis"""
        try:
            current_time = int(time.time())
            
            # Check per-minute limit
            minute_key = f"rate:{client_id}:{endpoint_key}:minute:{current_time // 60}"
            minute_count = await self.redis_client.incr(minute_key)
            await self.redis_client.expire(minute_key, 60)
            
            if minute_count > self.requests_per_minute:
                return False, {
                    "error": "Rate limit exceeded",
                    "limit": self.requests_per_minute,
                    "window": "minute",
                    "retry_after": 60 - (current_time % 60)
                }
            
            # Check per-hour limit
            hour_key = f"rate:{client_id}:{endpoint_key}:hour:{current_time // 3600}"
            hour_count = await self.redis_client.incr(hour_key)
            await self.redis_client.expire(hour_key, 3600)
            
            if hour_count > self.requests_per_hour:
                return False, {
                    "error": "Rate limit exceeded",
                    "limit": self.requests_per_hour,
                    "window": "hour",
                    "retry_after": 3600 - (current_time % 3600)
                }
            
            # Check per-day limit
            day_key = f"rate:{client_id}:{endpoint_key}:day:{current_time // 86400}"
            day_count = await self.redis_client.incr(day_key)
            await self.redis_client.expire(day_key, 86400)
            
            if day_count > self.requests_per_day:
                return False, {
                    "error": "Rate limit exceeded",
                    "limit": self.requests_per_day,
                    "window": "day",
                    "retry_after": 86400 - (current_time % 86400)
                }
            
            return True, {
                "requests_remaining": {
                    "minute": self.requests_per_minute - minute_count,
                    "hour": self.requests_per_hour - hour_count,
                    "day": self.requests_per_day - day_count
                }
            }
            
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            # Fall back to in-memory
            return self._check_sliding_window(client_id)
    
    def _check_sliding_window(self, client_id: str) -> Tuple[bool, Optional[Dict]]:
        """Sliding window rate limiting"""
        current_time = time.time()
        history = self.request_history[client_id]
        
        # Remove old requests outside the window
        minute_ago = current_time - 60
        hour_ago = current_time - 3600
        day_ago = current_time - 86400
        
        # Count requests in different windows
        minute_count = sum(1 for t in history if t > minute_ago)
        hour_count = sum(1 for t in history if t > hour_ago)
        day_count = len(history)
        
        # Check limits
        if minute_count >= self.requests_per_minute:
            self._mark_suspicious(client_id)
            return False, {
                "error": "Rate limit exceeded",
                "limit": self.requests_per_minute,
                "window": "minute",
                "retry_after": 60
            }
        
        if hour_count >= self.requests_per_hour:
            self._mark_suspicious(client_id)
            return False, {
                "error": "Rate limit exceeded",
                "limit": self.requests_per_hour,
                "window": "hour",
                "retry_after": 3600
            }
        
        if day_count >= self.requests_per_day:
            self._mark_suspicious(client_id)
            return False, {
                "error": "Rate limit exceeded",
                "limit": self.requests_per_day,
                "window": "day",
                "retry_after": 86400
            }
        
        # Add current request to history
        history.append(current_time)
        
        return True, {
            "requests_remaining": {
                "minute": self.requests_per_minute - minute_count - 1,
                "hour": self.requests_per_hour - hour_count - 1,
                "day": self.requests_per_day - day_count - 1
            }
        }
    
    def _check_token_bucket(self, client_id: str) -> Tuple[bool, Optional[Dict]]:
        """Token bucket rate limiting"""
        current_time = time.time()
        bucket = self.token_buckets[client_id]
        
        # Refill tokens based on time elapsed
        time_elapsed = current_time - bucket['last_refill']
        tokens_to_add = time_elapsed * (self.requests_per_minute / 60)
        
        bucket['tokens'] = min(
            self.burst_size,
            bucket['tokens'] + tokens_to_add
        )
        bucket['last_refill'] = current_time
        
        # Check if tokens available
        if bucket['tokens'] >= 1:
            bucket['tokens'] -= 1
            return True, {
                "tokens_remaining": int(bucket['tokens']),
                "burst_size": self.burst_size
            }
        
        self._mark_suspicious(client_id)
        return False, {
            "error": "Rate limit exceeded",
            "retry_after": (1 - bucket['tokens']) / (self.requests_per_minute / 60)
        }
    
    def _check_fixed_window(self, client_id: str) -> Tuple[bool, Optional[Dict]]:
        """Fixed window rate limiting"""
        current_minute = int(time.time() / 60)
        history = self.request_history[client_id]
        
        # Filter requests in current minute
        current_requests = [t for t in history if int(t / 60) == current_minute]
        
        if len(current_requests) >= self.requests_per_minute:
            self._mark_suspicious(client_id)
            return False, {
                "error": "Rate limit exceeded",
                "limit": self.requests_per_minute,
                "retry_after": 60 - (time.time() % 60)
            }
        
        history.append(time.time())
        return True, {
            "requests_remaining": self.requests_per_minute - len(current_requests) - 1
        }
    
    def _mark_suspicious(self, client_id: str):
        """Mark client as suspicious after multiple violations"""
        if client_id.startswith("ip:"):
            ip = client_id[3:]
            self.suspicious_ips[ip] += 1
            
            # Block IP after multiple violations
            if self.suspicious_ips[ip] >= 10:
                self.blocked_ips.add(ip)
                logger.warning(f"Blocked IP {ip} due to excessive rate limit violations")
    
    def unblock_ip(self, ip: str):
        """Unblock an IP address"""
        self.blocked_ips.discard(ip)
        self.suspicious_ips.pop(ip, None)
        logger.info(f"Unblocked IP {ip}")
    
    def get_stats(self) -> Dict:
        """Get rate limiting statistics"""
        return {
            "blocked_ips": list(self.blocked_ips),
            "suspicious_ips": dict(self.suspicious_ips),
            "active_clients": len(self.request_history),
            "redis_connected": self.redis_client is not None
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting"""
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        requests_per_day: int = 10000,
        exclude_paths: Optional[list] = None,
        redis_url: Optional[str] = None
    ):
        super().__init__(app)
        self.rate_limiter = RateLimiter(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            requests_per_day=requests_per_day,
            use_redis=bool(redis_url),
            redis_url=redis_url
        )
        self.exclude_paths = exclude_paths or ['/health', '/metrics']
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        
        # Skip rate limiting for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # Check rate limit
        allowed, info = await self.rate_limiter.check_rate_limit(request)
        
        if not allowed:
            # Return 429 Too Many Requests
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": info.get("error", "Rate limit exceeded"),
                    "retry_after": info.get("retry_after", 60)
                },
                headers={
                    "Retry-After": str(int(info.get("retry_after", 60))),
                    "X-RateLimit-Limit": str(self.rate_limiter.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time() + info.get("retry_after", 60)))
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        if info and "requests_remaining" in info:
            remaining = info["requests_remaining"]
            response.headers["X-RateLimit-Limit"] = str(self.rate_limiter.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(remaining.get("minute", 0))
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + 60))
        
        return response


# Decorator for custom rate limits on specific endpoints
def rate_limit(
    requests_per_minute: Optional[int] = None,
    requests_per_hour: Optional[int] = None,
    requests_per_day: Optional[int] = None
):
    """Decorator to apply custom rate limits to specific endpoints"""
    def decorator(func):
        func._rate_limit = {
            "requests_per_minute": requests_per_minute,
            "requests_per_hour": requests_per_hour,
            "requests_per_day": requests_per_day
        }
        return func
    return decorator


# Singleton instance
_rate_limiter = None

def get_rate_limiter() -> RateLimiter:
    """Get singleton rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter