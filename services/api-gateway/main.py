"""
API Gateway - Central entry point for all client requests
Handles authentication, rate limiting, and request routing
"""

from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import httpx
import redis.asyncio as redis
import json
import time
from typing import Optional, Dict, Any
import os
from datetime import datetime, timedelta
import structlog

from models import (
    AnalyticsRequest, 
    SentimentRequest, 
    TrendingRequest,
    APIResponse,
    UserCreate,
    UserLogin,
    RateLimitInfo
)
from auth import AuthManager
from rate_limiter import RateLimiter

# Configure structured logging
logger = structlog.get_logger()

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://localhost:8001")
ANALYTICS_SERVICE_URL = os.getenv("ANALYTICS_SERVICE_URL", "http://localhost:8002")

# Global variables
redis_client: Optional[redis.Redis] = None
http_client: Optional[httpx.AsyncClient] = None
auth_manager: Optional[AuthManager] = None
rate_limiter: Optional[RateLimiter] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global redis_client, http_client, auth_manager, rate_limiter
    
    # Startup
    logger.info("Starting API Gateway...")
    
    # Initialize Redis connection
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    await redis_client.ping()
    logger.info("Redis connection established")
    
    # Initialize HTTP client
    http_client = httpx.AsyncClient(timeout=30.0)
    logger.info("HTTP client initialized")
    
    # Initialize auth manager and rate limiter
    auth_manager = AuthManager(redis_client)
    rate_limiter = RateLimiter(redis_client)
    
    logger.info("API Gateway started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down API Gateway...")
    if http_client:
        await http_client.aclose()
    if redis_client:
        await redis_client.close()
    logger.info("API Gateway shutdown complete")

# Initialize FastAPI app
app = FastAPI(
    title="Social Media Analytics API Gateway",
    description="Central API gateway for real-time social media analytics platform",
    version="1.0.0",
    lifespan=lifespan
)

# Security
security = HTTPBearer(auto_error=False)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.localhost"]
)

# Dependency for authentication
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract and validate user from JWT token"""
    if not credentials:
        return None
    
    try:
        user_data = await auth_manager.verify_token(credentials.credentials)
        return user_data
    except Exception as e:
        logger.warning("Token verification failed", error=str(e))
        return None

# Dependency for rate limiting
async def check_rate_limit(request: Request, user_data: dict = Depends(get_current_user)):
    """Check rate limits for the current request"""
    client_id = user_data.get("user_id") if user_data else request.client.host
    
    is_allowed, limit_info = await rate_limiter.check_limit(
        client_id=client_id,
        endpoint=request.url.path,
        is_authenticated=user_data is not None
    )
    
    if not is_allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Rate limit exceeded",
                "limit_info": limit_info.dict()
            }
        )
    
    return limit_info

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check Redis connection
        await redis_client.ping()
        
        # Check downstream services
        ml_health = await check_service_health(ML_SERVICE_URL)
        analytics_health = await check_service_health(ANALYTICS_SERVICE_URL)
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "redis": "healthy",
                "ml_service": "healthy" if ml_health else "unhealthy",
                "analytics_service": "healthy" if analytics_health else "unhealthy"
            }
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unhealthy")

async def check_service_health(service_url: str) -> bool:
    """Check if a downstream service is healthy"""
    try:
        response = await http_client.get(f"{service_url}/health", timeout=5.0)
        return response.status_code == 200
    except:
        return False

# Authentication endpoints
@app.post("/auth/register", response_model=APIResponse)
async def register_user(user_data: UserCreate):
    """Register a new user"""
    try:
        result = await auth_manager.create_user(user_data)
        return APIResponse(
            success=True,
            data=result,
            message="User registered successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("User registration failed", error=str(e))
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/auth/login", response_model=APIResponse)
async def login_user(login_data: UserLogin):
    """Authenticate user and return JWT token"""
    try:
        result = await auth_manager.authenticate_user(login_data)
        return APIResponse(
            success=True,
            data=result,
            message="Login successful"
        )
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error("User login failed", error=str(e))
        raise HTTPException(status_code=500, detail="Login failed")

@app.post("/auth/logout", response_model=APIResponse)
async def logout_user(user_data: dict = Depends(get_current_user)):
    """Logout user and invalidate token"""
    if not user_data:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        await auth_manager.logout_user(user_data["user_id"])
        return APIResponse(
            success=True,
            message="Logout successful"
        )
    except Exception as e:
        logger.error("User logout failed", error=str(e))
        raise HTTPException(status_code=500, detail="Logout failed")

# ML Service endpoints
@app.post("/ml/sentiment", response_model=APIResponse)
async def analyze_sentiment(
    request: SentimentRequest,
    rate_limit: RateLimitInfo = Depends(check_rate_limit),
    user_data: dict = Depends(get_current_user)
):
    """Analyze sentiment of text using ML service"""
    try:
        response = await http_client.post(
            f"{ML_SERVICE_URL}/sentiment",
            json=request.dict(),
            headers={"X-User-ID": user_data.get("user_id", "anonymous") if user_data else "anonymous"}
        )
        response.raise_for_status()
        
        result = response.json()
        return APIResponse(
            success=True,
            data=result,
            message="Sentiment analysis completed"
        )
    except httpx.HTTPError as e:
        logger.error("ML service request failed", error=str(e))
        raise HTTPException(status_code=502, detail="ML service unavailable")
    except Exception as e:
        logger.error("Sentiment analysis failed", error=str(e))
        raise HTTPException(status_code=500, detail="Analysis failed")

@app.post("/ml/extract-entities", response_model=APIResponse)
async def extract_entities(
    request: SentimentRequest,  # Reusing same model for text input
    rate_limit: RateLimitInfo = Depends(check_rate_limit),
    user_data: dict = Depends(get_current_user)
):
    """Extract named entities from text"""
    try:
        response = await http_client.post(
            f"{ML_SERVICE_URL}/extract-entities",
            json=request.dict(),
            headers={"X-User-ID": user_data.get("user_id", "anonymous") if user_data else "anonymous"}
        )
        response.raise_for_status()
        
        result = response.json()
        return APIResponse(
            success=True,
            data=result,
            message="Entity extraction completed"
        )
    except httpx.HTTPError as e:
        logger.error("ML service request failed", error=str(e))
        raise HTTPException(status_code=502, detail="ML service unavailable")
    except Exception as e:
        logger.error("Entity extraction failed", error=str(e))
        raise HTTPException(status_code=500, detail="Extraction failed")

# Analytics Service endpoints
@app.get("/analytics/trending", response_model=APIResponse)
async def get_trending_topics(
    limit: int = 10,
    timeframe: str = "1h",
    rate_limit: RateLimitInfo = Depends(check_rate_limit),
    user_data: dict = Depends(get_current_user)
):
    """Get trending topics from analytics service"""
    try:
        params = {"limit": limit, "timeframe": timeframe}
        response = await http_client.get(
            f"{ANALYTICS_SERVICE_URL}/trending",
            params=params,
            headers={"X-User-ID": user_data.get("user_id", "anonymous") if user_data else "anonymous"}
        )
        response.raise_for_status()
        
        result = response.json()
        return APIResponse(
            success=True,
            data=result,
            message="Trending topics retrieved"
        )
    except httpx.HTTPError as e:
        logger.error("Analytics service request failed", error=str(e))
        raise HTTPException(status_code=502, detail="Analytics service unavailable")
    except Exception as e:
        logger.error("Trending topics request failed", error=str(e))
        raise HTTPException(status_code=500, detail="Request failed")

@app.get("/analytics/sentiment-overview", response_model=APIResponse)
async def get_sentiment_overview(
    timeframe: str = "24h",
    rate_limit: RateLimitInfo = Depends(check_rate_limit),
    user_data: dict = Depends(get_current_user)
):
    """Get sentiment overview from analytics service"""
    try:
        params = {"timeframe": timeframe}
        response = await http_client.get(
            f"{ANALYTICS_SERVICE_URL}/sentiment-overview",
            params=params,
            headers={"X-User-ID": user_data.get("user_id", "anonymous") if user_data else "anonymous"}
        )
        response.raise_for_status()
        
        result = response.json()
        return APIResponse(
            success=True,
            data=result,
            message="Sentiment overview retrieved"
        )
    except httpx.HTTPError as e:
        logger.error("Analytics service request failed", error=str(e))
        raise HTTPException(status_code=502, detail="Analytics service unavailable")
    except Exception as e:
        logger.error("Sentiment overview request failed", error=str(e))
        raise HTTPException(status_code=500, detail="Request failed")

@app.get("/analytics/metrics", response_model=APIResponse)
async def get_platform_metrics(
    rate_limit: RateLimitInfo = Depends(check_rate_limit),
    user_data: dict = Depends(get_current_user)
):
    """Get platform-wide metrics"""
    try:
        response = await http_client.get(
            f"{ANALYTICS_SERVICE_URL}/metrics",
            headers={"X-User-ID": user_data.get("user_id", "anonymous") if user_data else "anonymous"}
        )
        response.raise_for_status()
        
        result = response.json()
        return APIResponse(
            success=True,
            data=result,
            message="Platform metrics retrieved"
        )
    except httpx.HTTPError as e:
        logger.error("Analytics service request failed", error=str(e))
        raise HTTPException(status_code=502, detail="Analytics service unavailable")
    except Exception as e:
        logger.error("Platform metrics request failed", error=str(e))
        raise HTTPException(status_code=500, detail="Request failed")

# Real-time data endpoints
@app.get("/realtime/stats", response_model=APIResponse)
async def get_realtime_stats(
    rate_limit: RateLimitInfo = Depends(check_rate_limit)
):
    """Get real-time platform statistics"""
    try:
        # Get stats from Redis cache
        stats_key = "realtime:stats"
        cached_stats = await redis_client.get(stats_key)
        
        if cached_stats:
            stats = json.loads(cached_stats)
        else:
            # Fallback to basic stats
            stats = {
                "active_users": 0,
                "posts_processed_today": 0,
                "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0},
                "trending_topics_count": 0,
                "last_updated": datetime.utcnow().isoformat()
            }
        
        return APIResponse(
            success=True,
            data=stats,
            message="Real-time stats retrieved"
        )
    except Exception as e:
        logger.error("Real-time stats request failed", error=str(e))
        raise HTTPException(status_code=500, detail="Request failed")

# Admin endpoints (require authentication)
@app.get("/admin/system-status", response_model=APIResponse)
async def get_system_status(user_data: dict = Depends(get_current_user)):
    """Get detailed system status (admin only)"""
    if not user_data or not user_data.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Collect system metrics
        redis_info = await redis_client.info()
        
        system_status = {
            "redis": {
                "connected_clients": redis_info.get("connected_clients", 0),
                "used_memory_human": redis_info.get("used_memory_human", "0B"),
                "uptime_in_seconds": redis_info.get("uptime_in_seconds", 0)
            },
            "services": {
                "ml_service": await check_service_health(ML_SERVICE_URL),
                "analytics_service": await check_service_health(ANALYTICS_SERVICE_URL)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return APIResponse(
            success=True,
            data=system_status,
            message="System status retrieved"
        )
    except Exception as e:
        logger.error("System status request failed", error=str(e))
        raise HTTPException(status_code=500, detail="Request failed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)