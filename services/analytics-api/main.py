"""
Analytics API Service
Provides analytics endpoints for social media data analysis
"""

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncpg
import redis.asyncio as redis
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import structlog

from models import (
    TrendingTopicsResponse, SentimentDistributionResponse,
    PlatformMetricsResponse, TimeSeriesResponse, AnalyticsQuery
)

# Configure logging
logger = structlog.get_logger()

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://analytics_user:analytics_pass@localhost:5432/social_analytics")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Global variables
db_pool: Optional[asyncpg.Pool] = None
redis_client: Optional[redis.Redis] = None

class AnalyticsService:
    def __init__(self, db_pool: asyncpg.Pool, redis_client: redis.Redis):
        self.db = db_pool
        self.redis = redis_client
        
    async def get_trending_topics(self, platform: Optional[str] = None, 
                                 hours: int = 24, limit: int = 10) -> Dict[str, Any]:
        """Get trending topics for specified time period"""
        try:
            # Check cache first
            cache_key = f"trending:{platform or 'all'}:{hours}:{limit}"
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Query database
            async with self.db.acquire() as conn:
                query = """
                SELECT * FROM get_trending_topics($1, $2, $3)
                """
                rows = await conn.fetch(query, platform, hours, limit)
                
                topics = []
                for row in rows:
                    topics.append({
                        "topic": row["topic"],
                        "mentions": row["mentions"],
                        "sentiment_score": float(row["sentiment_score"]) if row["sentiment_score"] else 0.0,
                        "growth_rate": float(row["growth_rate"]) if row["growth_rate"] else 0.0,
                        "platforms": row["platforms"]
                    })
                
                result = {
                    "topics": topics,
                    "timeframe": f"{hours}h",
                    "platform": platform or "all",
                    "total_topics": len(topics),
                    "last_updated": datetime.utcnow().isoformat()
                }
                
                # Cache for 5 minutes
                await self.redis.setex(cache_key, 300, json.dumps(result, default=str))
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to get trending topics: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve trending topics")
    
    async def get_sentiment_distribution(self, platform: Optional[str] = None, 
                                       hours: int = 24) -> Dict[str, Any]:
        """Get sentiment distribution for specified time period"""
        try:
            cache_key = f"sentiment_dist:{platform or 'all'}:{hours}"
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
            
            async with self.db.acquire() as conn:
                query = """
                SELECT * FROM get_sentiment_distribution($1, $2)
                """
                rows = await conn.fetch(query, platform, hours)
                
                distribution = {}
                total = 0
                
                for row in rows:
                    sentiment = row["sentiment"]
                    count = row["count"]
                    percentage = float(row["percentage"])
                    
                    distribution[sentiment] = {
                        "count": count,
                        "percentage": percentage
                    }
                    total += count
                
                # Get time series data for trend
                trend_query = """
                SELECT 
                    time_bucket('1 hour', timestamp) as hour,
                    sentiment,
                    COUNT(*) as count
                FROM social_posts 
                WHERE timestamp >= NOW() - INTERVAL '%s hours'
                    AND (%s IS NULL OR platform = %s)
                    AND sentiment IS NOT NULL
                GROUP BY hour, sentiment
                ORDER BY hour
                """
                
                trend_rows = await conn.fetch(trend_query.replace('%s', '$1').replace('%s', '$2').replace('%s', '$3'), 
                                            hours, platform, platform)
                
                trend_data = []
                for row in trend_rows:
                    trend_data.append({
                        "timestamp": row["hour"].isoformat(),
                        "sentiment": row["sentiment"],
                        "count": row["count"]
                    })
                
                result = {
                    "distribution": distribution,
                    "total_posts": total,
                    "timeframe": f"{hours}h",
                    "platform": platform or "all",
                    "trend_data": trend_data,
                    "last_updated": datetime.utcnow().isoformat()
                }
                
                # Cache for 5 minutes
                await self.redis.setex(cache_key, 300, json.dumps(result, default=str))
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to get sentiment distribution: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve sentiment distribution")
    
    async def get_platform_metrics(self) -> Dict[str, Any]:
        """Get metrics for all platforms"""
        try:
            cache_key = "platform_metrics"
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
            
            async with self.db.acquire() as conn:
                # Get platform statistics
                query = """
                SELECT 
                    platform,
                    COUNT(*) as total_posts,
                    COUNT(DISTINCT author) as unique_users,
                    AVG(likes_count + shares_count + comments_count) as avg_engagement,
                    COUNT(CASE WHEN sentiment = 'positive' THEN 1 END) as positive_count,
                    COUNT(CASE WHEN sentiment = 'negative' THEN 1 END) as negative_count,
                    COUNT(CASE WHEN sentiment = 'neutral' THEN 1 END) as neutral_count
                FROM social_posts 
                WHERE timestamp >= NOW() - INTERVAL '24 hours'
                GROUP BY platform
                ORDER BY total_posts DESC
                """
                
                rows = await conn.fetch(query)
                
                platforms = []
                total_posts = 0
                total_users = 0
                
                for row in rows:
                    platform_data = {
                        "platform": row["platform"],
                        "total_posts": row["total_posts"],
                        "unique_users": row["unique_users"],
                        "avg_engagement": float(row["avg_engagement"]) if row["avg_engagement"] else 0.0,
                        "sentiment_distribution": {
                            "positive": row["positive_count"],
                            "negative": row["negative_count"],
                            "neutral": row["neutral_count"]
                        }
                    }
                    platforms.append(platform_data)
                    total_posts += row["total_posts"]
                    total_users += row["unique_users"]
                
                # Get top hashtags
                hashtag_query = """
                SELECT 
                    unnest(hashtags) as hashtag,
                    COUNT(*) as count
                FROM social_posts 
                WHERE timestamp >= NOW() - INTERVAL '24 hours'
                    AND hashtags IS NOT NULL
                GROUP BY hashtag
                ORDER BY count DESC
                LIMIT 20
                """
                
                hashtag_rows = await conn.fetch(hashtag_query)
                top_hashtags = [{"hashtag": row["hashtag"], "count": row["count"]} 
                              for row in hashtag_rows]
                
                result = {
                    "platforms": platforms,
                    "summary": {
                        "total_posts": total_posts,
                        "total_unique_users": total_users,
                        "active_platforms": len(platforms)
                    },
                    "top_hashtags": top_hashtags,
                    "timeframe": "24h",
                    "last_updated": datetime.utcnow().isoformat()
                }
                
                # Cache for 10 minutes
                await self.redis.setex(cache_key, 600, json.dumps(result, default=str))
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to get platform metrics: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve platform metrics")
    
    async def get_time_series_data(self, metric: str, platform: Optional[str] = None, 
                                  hours: int = 24, interval: str = "1h") -> Dict[str, Any]:
        """Get time series data for specified metric"""
        try:
            cache_key = f"timeseries:{metric}:{platform or 'all'}:{hours}:{interval}"
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Map interval to PostgreSQL interval
            interval_map = {
                "5m": "5 minutes",
                "15m": "15 minutes", 
                "1h": "1 hour",
                "6h": "6 hours",
                "1d": "1 day"
            }
            
            pg_interval = interval_map.get(interval, "1 hour")
            
            async with self.db.acquire() as conn:
                if metric == "post_volume":
                    query = """
                    SELECT 
                        time_bucket($1::interval, timestamp) as bucket,
                        COUNT(*) as value
                    FROM social_posts 
                    WHERE timestamp >= NOW() - INTERVAL '%s hours'
                        AND ($2 IS NULL OR platform = $2)
                    GROUP BY bucket
                    ORDER BY bucket
                    """
                    
                elif metric == "sentiment_trend":
                    query = """
                    SELECT 
                        time_bucket($1::interval, timestamp) as bucket,
                        sentiment,
                        COUNT(*) as value
                    FROM social_posts 
                    WHERE timestamp >= NOW() - INTERVAL '%s hours'
                        AND ($2 IS NULL OR platform = $2)
                        AND sentiment IS NOT NULL
                    GROUP BY bucket, sentiment
                    ORDER BY bucket, sentiment
                    """
                    
                elif metric == "engagement":
                    query = """
                    SELECT 
                        time_bucket($1::interval, timestamp) as bucket,
                        AVG(likes_count + shares_count + comments_count) as value
                    FROM social_posts 
                    WHERE timestamp >= NOW() - INTERVAL '%s hours'
                        AND ($2 IS NULL OR platform = $2)
                    GROUP BY bucket
                    ORDER BY bucket
                    """
                    
                else:
                    raise HTTPException(status_code=400, detail=f"Unknown metric: {metric}")
                
                query = query.replace('%s', str(hours))
                rows = await conn.fetch(query, pg_interval, platform)
                
                if metric == "sentiment_trend":
                    # Group by timestamp for sentiment trend
                    data_points = {}
                    for row in rows:
                        timestamp = row["bucket"].isoformat()
                        if timestamp not in data_points:
                            data_points[timestamp] = {"timestamp": timestamp}
                        data_points[timestamp][row["sentiment"]] = row["value"]
                    
                    time_series = list(data_points.values())
                else:
                    time_series = [
                        {
                            "timestamp": row["bucket"].isoformat(),
                            "value": float(row["value"]) if row["value"] else 0.0
                        }
                        for row in rows
                    ]
                
                result = {
                    "metric": metric,
                    "platform": platform or "all",
                    "interval": interval,
                    "timeframe": f"{hours}h",
                    "data_points": len(time_series),
                    "time_series": time_series,
                    "last_updated": datetime.utcnow().isoformat()
                }
                
                # Cache for 2 minutes
                await self.redis.setex(cache_key, 120, json.dumps(result, default=str))
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to get time series data: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve time series data")
    
    async def get_real_time_stats(self) -> Dict[str, Any]:
        """Get real-time platform statistics"""
        try:
            cache_key = "realtime_stats"
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
            
            async with self.db.acquire() as conn:
                # Get current stats
                stats_query = """
                SELECT 
                    COUNT(*) as posts_last_hour,
                    COUNT(DISTINCT author) as active_users_last_hour,
                    AVG(processing_time_ms) as avg_processing_time,
                    COUNT(CASE WHEN sentiment = 'positive' THEN 1 END) as positive_last_hour,
                    COUNT(CASE WHEN sentiment = 'negative' THEN 1 END) as negative_last_hour,
                    COUNT(CASE WHEN sentiment = 'neutral' THEN 1 END) as neutral_last_hour
                FROM social_posts 
                WHERE timestamp >= NOW() - INTERVAL '1 hour'
                """
                
                stats_row = await conn.fetchrow(stats_query)
                
                # Get posts per minute for last 10 minutes
                ppm_query = """
                SELECT 
                    time_bucket('1 minute', timestamp) as minute,
                    COUNT(*) as posts
                FROM social_posts 
                WHERE timestamp >= NOW() - INTERVAL '10 minutes'
                GROUP BY minute
                ORDER BY minute DESC
                LIMIT 10
                """
                
                ppm_rows = await conn.fetch(ppm_query)
                posts_per_minute = [row["posts"] for row in ppm_rows]
                avg_posts_per_minute = sum(posts_per_minute) / len(posts_per_minute) if posts_per_minute else 0
                
                # Get trending topics count
                trending_query = """
                SELECT COUNT(DISTINCT topic) as trending_count
                FROM trending_topics 
                WHERE time_window >= NOW() - INTERVAL '1 hour'
                """
                
                trending_row = await conn.fetchrow(trending_query)
                
                result = {
                    "posts_last_hour": stats_row["posts_last_hour"],
                    "active_users_last_hour": stats_row["active_users_last_hour"],
                    "posts_per_minute": avg_posts_per_minute,
                    "avg_processing_time_ms": float(stats_row["avg_processing_time"]) if stats_row["avg_processing_time"] else 0.0,
                    "sentiment_distribution": {
                        "positive": stats_row["positive_last_hour"],
                        "negative": stats_row["negative_last_hour"],
                        "neutral": stats_row["neutral_last_hour"]
                    },
                    "trending_topics_count": trending_row["trending_count"],
                    "posts_per_minute_trend": posts_per_minute,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Cache for 30 seconds
                await self.redis.setex(cache_key, 30, json.dumps(result, default=str))
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to get real-time stats: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve real-time stats")

# Initialize service
analytics_service: Optional[AnalyticsService] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global db_pool, redis_client, analytics_service
    
    # Startup
    logger.info("Starting Analytics API Service...")
    
    # Initialize database connection pool
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20)
    logger.info("Database connection pool created")
    
    # Initialize Redis connection
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    await redis_client.ping()
    logger.info("Redis connection established")
    
    # Initialize analytics service
    analytics_service = AnalyticsService(db_pool, redis_client)
    
    logger.info("Analytics API Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Analytics API Service...")
    if db_pool:
        await db_pool.close()
    if redis_client:
        await redis_client.close()
    logger.info("Analytics API Service shutdown complete")

# Initialize FastAPI app
app = FastAPI(
    title="Social Media Analytics API",
    description="Analytics API for social media data insights and metrics",
    version="1.0.0",
    lifespan=lifespan
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        
        # Check Redis
        await redis_client.ping()
        
        return {
            "status": "healthy",
            "database": "connected",
            "redis": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unhealthy")

# Analytics endpoints
@app.get("/trending")
async def get_trending_topics(
    platform: Optional[str] = Query(None, description="Platform to filter by"),
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of topics")
):
    """Get trending topics"""
    result = await analytics_service.get_trending_topics(platform, hours, limit)
    return {"success": True, "data": result}

@app.get("/sentiment-overview")
async def get_sentiment_overview(
    platform: Optional[str] = Query(None, description="Platform to filter by"),
    hours: int = Query(24, ge=1, le=168, description="Time window in hours")
):
    """Get sentiment distribution and trends"""
    result = await analytics_service.get_sentiment_distribution(platform, hours)
    return {"success": True, "data": result}

@app.get("/metrics")
async def get_platform_metrics():
    """Get platform-wide metrics"""
    result = await analytics_service.get_platform_metrics()
    return {"success": True, "data": result}

@app.get("/time-series/{metric}")
async def get_time_series(
    metric: str,
    platform: Optional[str] = Query(None, description="Platform to filter by"),
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    interval: str = Query("1h", regex="^(5m|15m|1h|6h|1d)$", description="Data interval")
):
    """Get time series data for specified metric"""
    result = await analytics_service.get_time_series_data(metric, platform, hours, interval)
    return {"success": True, "data": result}

@app.get("/realtime/stats")
async def get_realtime_stats():
    """Get real-time platform statistics"""
    result = await analytics_service.get_real_time_stats()
    return {"success": True, "data": result}

# Advanced analytics endpoints
@app.get("/insights/summary")
async def get_insights_summary(
    platform: Optional[str] = Query(None, description="Platform to filter by"),
    hours: int = Query(24, ge=1, le=168, description="Time window in hours")
):
    """Get AI-generated insights summary"""
    try:
        # Get multiple data sources
        trending = await analytics_service.get_trending_topics(platform, hours, 5)
        sentiment = await analytics_service.get_sentiment_distribution(platform, hours)
        metrics = await analytics_service.get_platform_metrics()
        
        # Generate insights (simplified version)
        insights = []
        
        # Trending insights
        if trending["topics"]:
            top_topic = trending["topics"][0]
            insights.append(f"'{top_topic['topic']}' is trending with {top_topic['mentions']} mentions")
        
        # Sentiment insights
        if sentiment["distribution"]:
            dominant_sentiment = max(sentiment["distribution"].items(), key=lambda x: x[1]["count"])
            insights.append(f"{dominant_sentiment[1]['percentage']:.1f}% of posts are {dominant_sentiment[0]}")
        
        # Platform insights
        if metrics["platforms"]:
            most_active = max(metrics["platforms"], key=lambda x: x["total_posts"])
            insights.append(f"{most_active['platform']} is the most active platform with {most_active['total_posts']} posts")
        
        result = {
            "insights": insights,
            "data_sources": {
                "trending_topics": len(trending["topics"]),
                "sentiment_posts": sentiment["total_posts"],
                "active_platforms": len(metrics["platforms"])
            },
            "timeframe": f"{hours}h",
            "generated_at": datetime.utcnow().isoformat()
        }
        
        return {"success": True, "data": result}
        
    except Exception as e:
        logger.error(f"Failed to generate insights: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate insights")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)