"""
Pydantic models for ML Service
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class LanguageCode(str, Enum):
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    DUTCH = "nl"
    RUSSIAN = "ru"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"
    ARABIC = "ar"

class SentimentType(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

class EmotionType(str, Enum):
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    LOVE = "love"

# Request models
class SentimentRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    language: LanguageCode = LanguageCode.ENGLISH
    include_emotions: bool = True
    
    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError('Text cannot be empty or only whitespace')
        return v.strip()

class EntityExtractionRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000)
    language: LanguageCode = LanguageCode.ENGLISH
    include_pos_tags: bool = False
    include_dependencies: bool = False
    
    @validator('text')
    def validate_text(cls, v):
        if not v.strip():
            raise ValueError('Text cannot be empty or only whitespace')
        return v.strip()

class TopicModelingRequest(BaseModel):
    texts: List[str] = Field(..., min_items=2, max_items=1000)
    num_topics: int = Field(5, ge=2, le=20)
    min_df: int = Field(2, ge=1)
    max_df: float = Field(0.8, gt=0.0, le=1.0)
    ngram_range: tuple = Field((1, 2))
    
    @validator('texts')
    def validate_texts(cls, v):
        if not all(text.strip() for text in v):
            raise ValueError('All texts must be non-empty')
        return [text.strip() for text in v]

class BatchProcessRequest(BaseModel):
    texts: List[str] = Field(..., min_items=1, max_items=100)
    operations: List[str] = Field(..., min_items=1)
    language: LanguageCode = LanguageCode.ENGLISH
    
    @validator('operations')
    def validate_operations(cls, v):
        valid_ops = {"sentiment", "entities", "topics", "emotions"}
        invalid_ops = set(v) - valid_ops
        if invalid_ops:
            raise ValueError(f'Invalid operations: {invalid_ops}. Valid: {valid_ops}')
        return v
    
    @validator('texts')
    def validate_texts(cls, v):
        if not all(text.strip() for text in v):
            raise ValueError('All texts must be non-empty')
        return [text.strip() for text in v]

# Response models
class SentimentScore(BaseModel):
    positive: float = Field(..., ge=0.0, le=1.0)
    negative: float = Field(..., ge=0.0, le=1.0)
    neutral: float = Field(..., ge=0.0, le=1.0)

class EmotionScores(BaseModel):
    joy: float = Field(0.0, ge=0.0, le=1.0)
    sadness: float = Field(0.0, ge=0.0, le=1.0)
    anger: float = Field(0.0, ge=0.0, le=1.0)
    fear: float = Field(0.0, ge=0.0, le=1.0)
    surprise: float = Field(0.0, ge=0.0, le=1.0)
    disgust: float = Field(0.0, ge=0.0, le=1.0)
    love: float = Field(0.0, ge=0.0, le=1.0)

class SentimentResponse(BaseModel):
    sentiment: SentimentType
    confidence: float = Field(..., ge=0.0, le=1.0)
    scores: SentimentScore
    emotions: Optional[EmotionScores] = None
    language_detected: Optional[str] = None
    processing_time_ms: float
    text_length: int
    cleaned_text_length: int

class Entity(BaseModel):
    text: str
    label: str
    description: Optional[str] = None
    start: int
    end: int
    confidence: float = Field(..., ge=0.0, le=1.0)

class POSTag(BaseModel):
    text: str
    pos: str
    tag: str
    lemma: str
    is_alpha: bool
    is_stop: bool

class EntityExtractionResponse(BaseModel):
    entities: List[Entity]
    tokens: Optional[List[str]] = None
    pos_tags: Optional[List[POSTag]] = None
    hashtags: List[str] = []
    mentions: List[str] = []
    urls: List[str] = []
    language_detected: Optional[str] = None
    processing_time_ms: float
    entity_count: int
    token_count: Optional[int] = None

class Topic(BaseModel):
    topic_id: int
    terms: List[str]
    scores: List[float]
    document_count: int
    sample_texts: List[str]
    coherence_score: Optional[float] = None

class TopicModelingResponse(BaseModel):
    topics: List[Topic]
    num_documents: int
    num_topics: int
    processing_time_ms: float
    cluster_assignments: List[int]
    overall_coherence: Optional[float] = None

class TextAnalysisResult(BaseModel):
    text_id: int
    original_text: str
    sentiment: Optional[SentimentResponse] = None
    entities: Optional[EntityExtractionResponse] = None
    emotions: Optional[EmotionScores] = None

class BatchProcessResponse(BaseModel):
    results: List[TextAnalysisResult]
    topics: Optional[TopicModelingResponse] = None
    total_texts: int
    operations_performed: List[str]
    processing_time_ms: float
    success_count: int
    error_count: int
    errors: Optional[List[Dict[str, Any]]] = None

# Model information
class ModelInfo(BaseModel):
    model_name: str
    model_type: str
    version: Optional[str] = None
    language_support: List[str]
    max_input_length: int
    device: str
    memory_usage_mb: Optional[float] = None
    load_time_seconds: Optional[float] = None

class ServiceInfo(BaseModel):
    service_name: str = "ML Service"
    version: str = "1.0.0"
    models: List[ModelInfo]
    device: str
    total_memory_mb: Optional[float] = None
    uptime_seconds: Optional[float] = None
    requests_processed: int = 0
    cache_hit_rate: Optional[float] = None

# Cache models
class CacheStats(BaseModel):
    total_cached_results: int
    cache_types: Dict[str, int]
    memory_usage_bytes: int
    hit_rate: float
    miss_rate: float
    eviction_count: int

class CacheEntry(BaseModel):
    key: str
    operation: str
    text_hash: str
    result: Dict[str, Any]
    created_at: datetime
    accessed_count: int
    last_accessed: datetime
    ttl_seconds: int

# Error models
class MLError(BaseModel):
    error_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ProcessingError(BaseModel):
    text_id: int
    operation: str
    error: MLError

# Monitoring models
class ModelPerformance(BaseModel):
    model_name: str
    total_requests: int
    average_processing_time_ms: float
    success_rate: float
    error_rate: float
    cache_hit_rate: float
    last_24h_requests: int

class ServiceMetrics(BaseModel):
    uptime_seconds: float
    total_requests: int
    requests_per_minute: float
    average_response_time_ms: float
    error_rate: float
    cache_hit_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float
    model_performance: List[ModelPerformance]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Configuration models
class ModelConfig(BaseModel):
    sentiment_model: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    emotion_model: str = "j-hartmann/emotion-english-distilroberta-base"
    ner_model: str = "en_core_web_sm"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    device: str = "auto"
    batch_size: int = 32
    max_length: int = 512
    cache_ttl_seconds: int = 3600

class ServiceConfig(BaseModel):
    model_config: ModelConfig
    redis_url: str = "redis://localhost:6379"
    log_level: str = "INFO"
    enable_cache: bool = True
    enable_metrics: bool = True
    max_concurrent_requests: int = 100
    request_timeout_seconds: int = 30

# Utility models
class TextPreprocessingOptions(BaseModel):
    remove_urls: bool = True
    remove_mentions: bool = False
    remove_hashtags: bool = False
    remove_punctuation: bool = False
    lowercase: bool = False
    remove_stopwords: bool = False
    min_length: int = 3
    max_length: int = 5000

class AnalysisOptions(BaseModel):
    include_confidence_scores: bool = True
    include_processing_time: bool = True
    include_metadata: bool = True
    preprocessing: TextPreprocessingOptions = TextPreprocessingOptions()
    cache_results: bool = True