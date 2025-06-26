"""
Authentication Manager
Handles user registration, login, JWT tokens, and session management
"""

import jwt
import bcrypt
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import redis.asyncio as redis
import json
import os
from models import UserCreate, UserLogin, UserResponse, TokenResponse

class AuthManager:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.jwt_secret = os.getenv("JWT_SECRET", "your-super-secret-jwt-key-change-in-production")
        self.jwt_algorithm = "HS256"
        self.token_expiry_hours = int(os.getenv("JWT_EXPIRY_HOURS", "24"))
        
    async def create_user(self, user_data: UserCreate) -> Dict[str, Any]:
        """Create a new user account"""
        # Check if username or email already exists
        existing_user = await self._get_user_by_username(user_data.username)
        if existing_user:
            raise ValueError("Username already exists")
            
        existing_email = await self._get_user_by_email(user_data.email)
        if existing_email:
            raise ValueError("Email already exists")
        
        # Hash password
        password_hash = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt())
        
        # Create user record
        user_id = str(uuid.uuid4())
        user_record = {
            "user_id": user_id,
            "username": user_data.username,
            "email": user_data.email,
            "password_hash": password_hash.decode('utf-8'),
            "full_name": user_data.full_name,
            "is_admin": False,
            "created_at": datetime.utcnow().isoformat(),
            "last_login": None,
            "is_active": True
        }
        
        # Store in Redis
        await self.redis.hset(f"user:{user_id}", mapping=user_record)
        await self.redis.set(f"username:{user_data.username}", user_id)
        await self.redis.set(f"email:{user_data.email}", user_id)
        
        # Create and return token
        token_data = await self._create_token(user_record)
        
        return {
            "user": UserResponse(**{k: v for k, v in user_record.items() 
                                 if k != "password_hash"}),
            "token": token_data
        }
    
    async def authenticate_user(self, login_data: UserLogin) -> Dict[str, Any]:
        """Authenticate user and return JWT token"""
        # Get user by username
        user_record = await self._get_user_by_username(login_data.username)
        if not user_record:
            raise ValueError("Invalid username or password")
        
        # Verify password
        if not bcrypt.checkpw(login_data.password.encode('utf-8'), 
                             user_record["password_hash"].encode('utf-8')):
            raise ValueError("Invalid username or password")
        
        # Check if user is active
        if not user_record.get("is_active", True):
            raise ValueError("Account is deactivated")
        
        # Update last login
        user_record["last_login"] = datetime.utcnow().isoformat()
        await self.redis.hset(f"user:{user_record['user_id']}", 
                             "last_login", user_record["last_login"])
        
        # Create and return token
        token_data = await self._create_token(user_record)
        
        return {
            "user": UserResponse(**{k: v for k, v in user_record.items() 
                                 if k != "password_hash"}),
            "token": token_data
        }
    
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and return user data"""
        try:
            # Decode token
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Check if token is blacklisted
            is_blacklisted = await self.redis.get(f"blacklist:{token}")
            if is_blacklisted:
                raise ValueError("Token has been revoked")
            
            # Get user data
            user_id = payload.get("user_id")
            if not user_id:
                raise ValueError("Invalid token payload")
            
            user_record = await self._get_user_by_id(user_id)
            if not user_record:
                raise ValueError("User not found")
            
            if not user_record.get("is_active", True):
                raise ValueError("Account is deactivated")
            
            return {k: v for k, v in user_record.items() if k != "password_hash"}
            
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")
    
    async def logout_user(self, user_id: str, token: Optional[str] = None) -> bool:
        """Logout user and optionally blacklist token"""
        if token:
            # Add token to blacklist
            expiry = timedelta(hours=self.token_expiry_hours)
            await self.redis.setex(f"blacklist:{token}", expiry, "1")
        
        # Could also invalidate all user sessions here if needed
        return True
    
    async def refresh_token(self, token: str) -> Dict[str, Any]:
        """Refresh an existing JWT token"""
        user_data = await self.verify_token(token)
        
        # Blacklist old token
        expiry = timedelta(hours=self.token_expiry_hours)
        await self.redis.setex(f"blacklist:{token}", expiry, "1")
        
        # Create new token
        return await self._create_token(user_data)
    
    async def _create_token(self, user_record: Dict[str, Any]) -> Dict[str, Any]:
        """Create JWT token for user"""
        expiry = datetime.utcnow() + timedelta(hours=self.token_expiry_hours)
        
        payload = {
            "user_id": user_record["user_id"],
            "username": user_record["username"],
            "is_admin": user_record.get("is_admin", False),
            "exp": expiry,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": self.token_expiry_hours * 3600,
            "expires_at": expiry.isoformat()
        }
    
    async def _get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user record by username"""
        user_id = await self.redis.get(f"username:{username}")
        if not user_id:
            return None
        return await self._get_user_by_id(user_id)
    
    async def _get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user record by email"""
        user_id = await self.redis.get(f"email:{email}")
        if not user_id:
            return None
        return await self._get_user_by_id(user_id)
    
    async def _get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user record by user ID"""
        user_data = await self.redis.hgetall(f"user:{user_id}")
        if not user_data:
            return None
        
        # Convert Redis hash to proper types
        user_record = {}
        for key, value in user_data.items():
            if key in ["is_admin", "is_active"]:
                user_record[key] = value.lower() == "true"
            else:
                user_record[key] = value
        
        return user_record
    
    async def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics and activity"""
        user_record = await self._get_user_by_id(user_id)
        if not user_record:
            return {}
        
        # Get user activity stats from Redis
        stats_key = f"user_stats:{user_id}"
        stats = await self.redis.hgetall(stats_key)
        
        return {
            "user_id": user_id,
            "username": user_record["username"],
            "member_since": user_record["created_at"],
            "last_login": user_record.get("last_login"),
            "total_requests": int(stats.get("total_requests", 0)),
            "requests_today": int(stats.get("requests_today", 0)),
            "favorite_endpoints": stats.get("favorite_endpoints", "").split(",") if stats.get("favorite_endpoints") else []
        }
    
    async def update_user_activity(self, user_id: str, endpoint: str):
        """Update user activity statistics"""
        stats_key = f"user_stats:{user_id}"
        
        # Increment counters
        await self.redis.hincrby(stats_key, "total_requests", 1)
        
        # Daily counter with expiry
        today = datetime.utcnow().strftime("%Y-%m-%d")
        daily_key = f"user_daily:{user_id}:{today}"
        await self.redis.incr(daily_key)
        await self.redis.expire(daily_key, 86400)  # Expire after 24 hours
        
        # Track endpoint usage
        endpoint_key = f"user_endpoints:{user_id}"
        await self.redis.zincrby(endpoint_key, 1, endpoint)
        
        # Keep only top 10 endpoints
        await self.redis.zremrangebyrank(endpoint_key, 0, -11)
    
    async def create_admin_user(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """Create an admin user (for initial setup)"""
        user_data = UserCreate(
            username=username,
            email=email,
            password=password,
            full_name="System Administrator"
        )
        
        result = await self.create_user(user_data)
        
        # Update user to admin
        user_id = result["user"]["user_id"]
        await self.redis.hset(f"user:{user_id}", "is_admin", "true")
        
        return result