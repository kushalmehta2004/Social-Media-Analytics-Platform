"""
Pydantic models for API Gateway
Defines request/response schemas and data validation
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from enum import Enum

class SentimentType(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

class TimeframeType(str, Enum):
    HOUR_1 = "1h"
    HOUR_6 = "6h"
    HOUR_24 = "24h"
    DAY_7 = "7d"
    DAY_30 = "30d"

class PlatformType(str, Enum):
    TWITTER = "twitter"
    REDDIT = "reddit"
    INSTAGRAM = "instagram"
    ALL = "all"

# Base response model
class APIResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Authentication models
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=100)
    
    @validator('username')
    def validate_username(cls, v):
        if not v.isalnum() and '_' not in v:
            raise ValueError('Username must contain only alphanumeric characters and underscores')
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    user_id: str
    username: str
    email: str
    full_name: Optional[str]
    is_admin: bool = False
    created_at: datetime
    last_login: Optional[datetime] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

# ML Service models
class SentimentRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    language: Optional[str] = Field("en", regex="^[a-z]{2}$")
    
    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError('Text cannot be empty or only whitespace')
        return v.strip()

class SentimentResponse(BaseModel):
    sentiment: SentimentType
    confidence: float = Field(..., ge=0.0, le=1.0)
    scores: Dict[str, float]
    language_detected: Optional[str] = None
    processing_time_ms: float

class EntityExtractionResponse(BaseModel):
    entities: List[Dict[str, Any]]
    processing_time_ms: float
    language_detected: Optional[str] = None

# Analytics models
class TrendingRequest(BaseModel):
    limit: int = Field(10, ge=1, le=100)
    timeframe: TimeframeType = TimeframeType.HOUR_24
    platform: PlatformType = PlatformType.ALL
    min_mentions: int = Field(5, ge=1)

class TrendingTopic(BaseModel):
    topic: str
    mentions: int
    sentiment_score: float
    platforms: List[str]
    growth_rate: float
    related_keywords: List[str]

class TrendingResponse(BaseModel):
    topics: List[TrendingTopic]
    timeframe: str
    total_topics: int
    last_updated: datetime

class SentimentOverviewRequest(BaseModel):
    timeframe: TimeframeType = TimeframeType.HOUR_24
    platform: PlatformType = PlatformType.ALL
    topic_filter: Optional[str] = None

class SentimentDistribution(BaseModel):
    positive: int
    negative: int
    neutral: int
    total: int
    
    @property
    def positive_percentage(self) -> float:
        return (self.positive / self.total * 100) if self.total > 0 else 0.0
    
    @property
    def negative_percentage(self) -> float:
        return (self.negative / self.total * 100) if self.total > 0 else 0.0
    
    @property
    def neutral_percentage(self) -> float:
        return (self.neutral / self.total * 100) if self.total > 0 else 0.0

class SentimentOverviewResponse(BaseModel):
    distribution: SentimentDistribution
    average_sentiment: float
    sentiment_trend: List[Dict[str, Any]]
    top_positive_topics: List[str]
    top_negative_topics: List[str]
    timeframe: str
    last_updated: datetime

# Analytics request models
class AnalyticsRequest(BaseModel):
    timeframe: TimeframeType = TimeframeType.HOUR_24
    platform: PlatformType = PlatformType.ALL
    metrics: List[str] = Field(default=["sentiment", "volume", "engagement"])
    
    @validator('metrics')
    def validate_metrics(cls, v):
        valid_metrics = {"sentiment", "volume", "engagement", "reach", "trending"}
        invalid_metrics = set(v) - valid_metrics
        if invalid_metrics:
            raise ValueError(f'Invalid metrics: {invalid_metrics}')
        return v

class PlatformMetrics(BaseModel):
    platform: str
    total_posts: int
    unique_users: int
    engagement_rate: float
    sentiment_distribution: SentimentDistribution
    top_hashtags: List[str]
    average_reach: float

class MetricsResponse(BaseModel):
    overall_metrics: Dict[str, Any]
    platform_breakdown: List[PlatformMetrics]
    time_series_data: List[Dict[str, Any]]
    insights: List[str]
    last_updated: datetime

# Rate limiting models
class RateLimitInfo(BaseModel):
    requests_remaining: int
    reset_time: datetime
    limit_per_window: int
    window_size_seconds: int

# Real-time data models
class RealtimeStats(BaseModel):
    active_users: int
    posts_processed_today: int
    posts_per_minute: float
    sentiment_distribution: SentimentDistribution
    trending_topics_count: int
    system_load: float
    last_updated: datetime

class WebSocketMessage(BaseModel):
    type: str
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Data ingestion models
class SocialMediaPost(BaseModel):
    post_id: str
    platform: PlatformType
    author: str
    content: str
    timestamp: datetime
    engagement_metrics: Dict[str, int]
    hashtags: List[str]
    mentions: List[str]
    location: Optional[str] = None
    language: Optional[str] = None

class ProcessedPost(SocialMediaPost):
    sentiment: SentimentType
    sentiment_confidence: float
    entities: List[Dict[str, Any]]
    topics: List[str]
    processed_at: datetime

# System monitoring models
class ServiceHealth(BaseModel):
    service_name: str
    status: str
    response_time_ms: float
    last_check: datetime
    error_message: Optional[str] = None

class SystemStatus(BaseModel):
    overall_status: str
    services: List[ServiceHealth]
    redis_stats: Dict[str, Any]
    database_stats: Dict[str, Any]
    system_resources: Dict[str, Any]
    timestamp: datetime

# Error models
class ErrorDetail(BaseModel):
    code: str
    message: str
    field: Optional[str] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Pagination models
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool

# Configuration models
class APIConfig(BaseModel):
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000
    max_request_size_mb: int = 10
    jwt_expiry_hours: int = 24
    enable_analytics: bool = True
    enable_real_time: bool = True