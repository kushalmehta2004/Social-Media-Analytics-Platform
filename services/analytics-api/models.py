"""
Pydantic models for Analytics API Service
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class PlatformType(str, Enum):
    TWITTER = "twitter"
    REDDIT = "reddit"
    INSTAGRAM = "instagram"
    ALL = "all"

class MetricType(str, Enum):
    POST_VOLUME = "post_volume"
    SENTIMENT_TREND = "sentiment_trend"
    ENGAGEMENT = "engagement"
    USER_ACTIVITY = "user_activity"

class TimeInterval(str, Enum):
    FIVE_MIN = "5m"
    FIFTEEN_MIN = "15m"
    ONE_HOUR = "1h"
    SIX_HOURS = "6h"
    ONE_DAY = "1d"

# Request models
class AnalyticsQuery(BaseModel):
    platform: Optional[PlatformType] = None
    hours: int = Field(24, ge=1, le=168)
    limit: int = Field(10, ge=1, le=100)

class TimeSeriesQuery(BaseModel):
    metric: MetricType
    platform: Optional[PlatformType] = None
    hours: int = Field(24, ge=1, le=168)
    interval: TimeInterval = TimeInterval.ONE_HOUR

# Response models
class TrendingTopic(BaseModel):
    topic: str
    mentions: int
    sentiment_score: float = Field(..., ge=-1.0, le=1.0)
    growth_rate: float
    platforms: List[str]
    related_keywords: Optional[List[str]] = []

class TrendingTopicsResponse(BaseModel):
    topics: List[TrendingTopic]
    timeframe: str
    platform: str
    total_topics: int
    last_updated: datetime

class SentimentDistribution(BaseModel):
    positive: Dict[str, Any]
    negative: Dict[str, Any]
    neutral: Dict[str, Any]

class SentimentTrendPoint(BaseModel):
    timestamp: datetime
    positive: int = 0
    negative: int = 0
    neutral: int = 0

class SentimentDistributionResponse(BaseModel):
    distribution: SentimentDistribution
    total_posts: int
    timeframe: str
    platform: str
    trend_data: List[Dict[str, Any]]
    last_updated: datetime

class PlatformMetrics(BaseModel):
    platform: str
    total_posts: int
    unique_users: int
    avg_engagement: float
    sentiment_distribution: Dict[str, int]

class HashtagInfo(BaseModel):
    hashtag: str
    count: int

class PlatformSummary(BaseModel):
    total_posts: int
    total_unique_users: int
    active_platforms: int

class PlatformMetricsResponse(BaseModel):
    platforms: List[PlatformMetrics]
    summary: PlatformSummary
    top_hashtags: List[HashtagInfo]
    timeframe: str
    last_updated: datetime

class TimeSeriesPoint(BaseModel):
    timestamp: datetime
    value: float

class SentimentTimeSeriesPoint(BaseModel):
    timestamp: datetime
    positive: Optional[int] = 0
    negative: Optional[int] = 0
    neutral: Optional[int] = 0

class TimeSeriesResponse(BaseModel):
    metric: str
    platform: str
    interval: str
    timeframe: str
    data_points: int
    time_series: List[Dict[str, Any]]
    last_updated: datetime

class RealtimeStats(BaseModel):
    posts_last_hour: int
    active_users_last_hour: int
    posts_per_minute: float
    avg_processing_time_ms: float
    sentiment_distribution: Dict[str, int]
    trending_topics_count: int
    posts_per_minute_trend: List[int]
    timestamp: datetime

class InsightsSummary(BaseModel):
    insights: List[str]
    data_sources: Dict[str, int]
    timeframe: str
    generated_at: datetime

# Database models
class SocialPost(BaseModel):
    post_id: str
    platform: str
    author: str
    content: str
    timestamp: datetime
    likes_count: int = 0
    shares_count: int = 0
    comments_count: int = 0
    retweets_count: int = 0
    hashtags: Optional[List[str]] = []
    mentions: Optional[List[str]] = []
    urls: Optional[List[str]] = []
    location: Optional[str] = None
    language: Optional[str] = None
    sentiment: Optional[str] = None
    sentiment_confidence: Optional[float] = None
    sentiment_scores: Optional[Dict[str, float]] = None
    emotions: Optional[Dict[str, float]] = None
    entities: Optional[List[Dict[str, Any]]] = None
    topics: Optional[List[str]] = []
    processed_at: Optional[datetime] = None
    processing_time_ms: Optional[int] = None

class TrendingTopicDB(BaseModel):
    id: int
    topic: str
    platform: str
    mentions_count: int
    sentiment_score: float
    growth_rate: float
    related_keywords: List[str]
    time_window: datetime
    created_at: datetime

class UserActivity(BaseModel):
    id: int
    user_id: str
    activity_type: str
    endpoint: Optional[str] = None
    request_data: Optional[Dict[str, Any]] = None
    response_status: Optional[int] = None
    processing_time_ms: Optional[int] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime

# Analytics aggregation models
class HourlySentimentStats(BaseModel):
    hour: datetime
    platform: str
    sentiment: str
    post_count: int
    avg_confidence: float
    avg_engagement: float

class DailyTrendingStats(BaseModel):
    day: datetime
    platform: str
    topic: str
    total_mentions: int
    avg_sentiment: float
    peak_growth_rate: float

class UserEngagementSummary(BaseModel):
    user_id: str
    username: str
    total_requests: int
    active_days: int
    avg_response_time: float
    last_activity: datetime

# Advanced analytics models
class TopicCluster(BaseModel):
    cluster_id: int
    topics: List[str]
    size: int
    avg_sentiment: float
    platforms: List[str]

class InfluencerMetrics(BaseModel):
    author: str
    platform: str
    total_posts: int
    avg_engagement: float
    follower_growth: float
    sentiment_impact: float
    reach_score: float

class ViralContent(BaseModel):
    post_id: str
    platform: str
    author: str
    content_preview: str
    engagement_score: float
    viral_coefficient: float
    peak_time: datetime
    sentiment: str

class PlatformComparison(BaseModel):
    metric: str
    platforms: Dict[str, float]
    winner: str
    difference_percentage: float

class TrendAnalysis(BaseModel):
    topic: str
    trend_direction: str  # "rising", "falling", "stable"
    velocity: float
    predicted_peak: Optional[datetime] = None
    confidence: float
    related_events: List[str]

# Error and status models
class AnalyticsError(BaseModel):
    error_type: str
    message: str
    query_params: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ServiceStatus(BaseModel):
    service: str = "Analytics API"
    status: str
    database_status: str
    redis_status: str
    uptime_seconds: float
    total_queries_processed: int
    avg_query_time_ms: float
    cache_hit_rate: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Configuration models
class AnalyticsConfig(BaseModel):
    cache_ttl_seconds: int = 300
    max_query_hours: int = 168  # 7 days
    default_limit: int = 10
    max_limit: int = 100
    enable_real_time: bool = True
    enable_caching: bool = True