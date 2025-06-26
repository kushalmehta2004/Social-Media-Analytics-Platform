"""
Rate Limiter
Implements sliding window rate limiting with Redis
"""

import time
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any
import redis.asyncio as redis
from models import RateLimitInfo

class RateLimiter:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        
        # Rate limit configurations
        self.limits = {
            # Anonymous users
            "anonymous": {
                "requests_per_minute": 20,
                "requests_per_hour": 100,
                "requests_per_day": 1000
            },
            # Authenticated users
            "authenticated": {
                "requests_per_minute": 60,
                "requests_per_hour": 1000,
                "requests_per_day": 10000
            },
            # Admin users
            "admin": {
                "requests_per_minute": 200,
                "requests_per_hour": 5000,
                "requests_per_day": 50000
            }
        }
        
        # Endpoint-specific limits
        self.endpoint_limits = {
            "/ml/sentiment": {
                "anonymous": {"requests_per_minute": 5, "requests_per_hour": 50},
                "authenticated": {"requests_per_minute": 30, "requests_per_hour": 500},
                "admin": {"requests_per_minute": 100, "requests_per_hour": 2000}
            },
            "/ml/extract-entities": {
                "anonymous": {"requests_per_minute": 3, "requests_per_hour": 30},
                "authenticated": {"requests_per_minute": 20, "requests_per_hour": 300},
                "admin": {"requests_per_minute": 80, "requests_per_hour": 1500}
            },
            "/analytics/trending": {
                "anonymous": {"requests_per_minute": 10, "requests_per_hour": 100},
                "authenticated": {"requests_per_minute": 30, "requests_per_hour": 500},
                "admin": {"requests_per_minute": 100, "requests_per_hour": 2000}
            }
        }
    
    async def check_limit(self, client_id: str, endpoint: str, 
                         is_authenticated: bool = False, is_admin: bool = False) -> Tuple[bool, RateLimitInfo]:
        """
        Check if request is within rate limits using sliding window algorithm
        Returns (is_allowed, rate_limit_info)
        """
        # Determine user type
        if is_admin:
            user_type = "admin"
        elif is_authenticated:
            user_type = "authenticated"
        else:
            user_type = "anonymous"
        
        # Get applicable limits
        general_limits = self.limits[user_type]
        endpoint_specific = self.endpoint_limits.get(endpoint, {}).get(user_type, {})
        
        # Check each time window
        current_time = time.time()
        windows = [
            ("minute", 60, endpoint_specific.get("requests_per_minute", general_limits["requests_per_minute"])),
            ("hour", 3600, endpoint_specific.get("requests_per_hour", general_limits["requests_per_hour"])),
            ("day", 86400, general_limits["requests_per_day"])
        ]
        
        for window_name, window_seconds, limit in windows:
            key = f"rate_limit:{client_id}:{endpoint}:{window_name}"
            
            # Use sliding window counter
            is_allowed, remaining, reset_time = await self._sliding_window_check(
                key, current_time, window_seconds, limit
            )
            
            if not is_allowed:
                rate_limit_info = RateLimitInfo(
                    requests_remaining=0,
                    reset_time=datetime.fromtimestamp(reset_time),
                    limit_per_window=limit,
                    window_size_seconds=window_seconds
                )
                return False, rate_limit_info
        
        # All checks passed, record the request
        await self._record_request(client_id, endpoint, current_time)
        
        # Return info for the most restrictive window (minute)
        minute_key = f"rate_limit:{client_id}:{endpoint}:minute"
        _, remaining, reset_time = await self._sliding_window_check(
            minute_key, current_time, 60, 
            endpoint_specific.get("requests_per_minute", general_limits["requests_per_minute"]),
            increment=False  # Don't increment again
        )
        
        rate_limit_info = RateLimitInfo(
            requests_remaining=remaining,
            reset_time=datetime.fromtimestamp(reset_time),
            limit_per_window=endpoint_specific.get("requests_per_minute", general_limits["requests_per_minute"]),
            window_size_seconds=60
        )
        
        return True, rate_limit_info
    
    async def _sliding_window_check(self, key: str, current_time: float, 
                                   window_seconds: int, limit: int, 
                                   increment: bool = True) -> Tuple[bool, int, float]:
        """
        Implement sliding window rate limiting
        Returns (is_allowed, remaining_requests, reset_time)
        """
        window_start = current_time - window_seconds
        
        # Use Redis pipeline for atomic operations
        pipe = self.redis.pipeline()
        
        # Remove expired entries
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count current requests in window
        pipe.zcard(key)
        
        # Execute pipeline
        results = await pipe.execute()
        current_count = results[1]
        
        # Check if limit exceeded
        if current_count >= limit:
            # Calculate reset time (when oldest entry expires)
            oldest_entries = await self.redis.zrange(key, 0, 0, withscores=True)
            if oldest_entries:
                reset_time = oldest_entries[0][1] + window_seconds
            else:
                reset_time = current_time + window_seconds
            
            return False, 0, reset_time
        
        # Add current request if incrementing
        if increment:
            await self.redis.zadd(key, {str(current_time): current_time})
            await self.redis.expire(key, window_seconds)
            current_count += 1
        
        remaining = limit - current_count
        reset_time = current_time + window_seconds
        
        return True, remaining, reset_time
    
    async def _record_request(self, client_id: str, endpoint: str, timestamp: float):
        """Record request for all time windows"""
        windows = [
            ("minute", 60),
            ("hour", 3600),
            ("day", 86400)
        ]
        
        pipe = self.redis.pipeline()
        
        for window_name, window_seconds in windows:
            key = f"rate_limit:{client_id}:{endpoint}:{window_name}"
            pipe.zadd(key, {str(timestamp): timestamp})
            pipe.expire(key, window_seconds)
        
        await pipe.execute()
    
    async def get_client_stats(self, client_id: str) -> Dict[str, Any]:
        """Get rate limiting statistics for a client"""
        current_time = time.time()
        stats = {}
        
        # Get all keys for this client
        pattern = f"rate_limit:{client_id}:*"
        keys = await self.redis.keys(pattern)
        
        for key in keys:
            parts = key.split(":")
            if len(parts) >= 4:
                endpoint = parts[2]
                window = parts[3]
                
                # Count requests in current window
                if window == "minute":
                    window_start = current_time - 60
                elif window == "hour":
                    window_start = current_time - 3600
                elif window == "day":
                    window_start = current_time - 86400
                else:
                    continue
                
                count = await self.redis.zcount(key, window_start, current_time)
                
                if endpoint not in stats:
                    stats[endpoint] = {}
                stats[endpoint][f"requests_last_{window}"] = count
        
        return stats
    
    async def reset_client_limits(self, client_id: str, endpoint: str = None):
        """Reset rate limits for a client (admin function)"""
        if endpoint:
            pattern = f"rate_limit:{client_id}:{endpoint}:*"
        else:
            pattern = f"rate_limit:{client_id}:*"
        
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
    
    async def get_global_stats(self) -> Dict[str, Any]:
        """Get global rate limiting statistics"""
        current_time = time.time()
        
        # Get all rate limit keys
        all_keys = await self.redis.keys("rate_limit:*")
        
        stats = {
            "total_clients": len(set(key.split(":")[1] for key in all_keys)),
            "active_endpoints": {},
            "requests_per_minute": 0,
            "requests_per_hour": 0,
            "top_clients": []
        }
        
        # Aggregate statistics
        client_counts = {}
        endpoint_counts = {}
        
        for key in all_keys:
            parts = key.split(":")
            if len(parts) >= 4:
                client_id = parts[1]
                endpoint = parts[2]
                window = parts[3]
                
                if window == "minute":
                    window_start = current_time - 60
                    count = await self.redis.zcount(key, window_start, current_time)
                    stats["requests_per_minute"] += count
                    
                    client_counts[client_id] = client_counts.get(client_id, 0) + count
                    endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + count
                
                elif window == "hour":
                    window_start = current_time - 3600
                    count = await self.redis.zcount(key, window_start, current_time)
                    stats["requests_per_hour"] += count
        
        # Top clients and endpoints
        stats["top_clients"] = sorted(client_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        stats["active_endpoints"] = dict(sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True))
        
        return stats
    
    async def cleanup_expired_entries(self):
        """Clean up expired rate limit entries (maintenance task)"""
        current_time = time.time()
        
        # Get all rate limit keys
        keys = await self.redis.keys("rate_limit:*")
        
        cleaned_count = 0
        for key in keys:
            # Determine window size from key
            if ":minute:" in key:
                window_start = current_time - 60
            elif ":hour:" in key:
                window_start = current_time - 3600
            elif ":day:" in key:
                window_start = current_time - 86400
            else:
                continue
            
            # Remove expired entries
            removed = await self.redis.zremrangebyscore(key, 0, window_start)
            cleaned_count += removed
            
            # Remove empty keys
            if await self.redis.zcard(key) == 0:
                await self.redis.delete(key)
        
        return cleaned_count