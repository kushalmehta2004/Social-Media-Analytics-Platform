"""
ML Service - Natural Language Processing and Machine Learning
Handles sentiment analysis, entity extraction, and topic modeling
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import time
import os
from typing import Dict, List, Any, Optional
import structlog
import redis.asyncio as redis
import json
from datetime import datetime

# ML and NLP imports
import torch
from transformers import (
    AutoTokenizer, AutoModelForSequenceClassification,
    pipeline, AutoModel
)
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import numpy as np
import re
from collections import Counter

from models import (
    SentimentRequest, SentimentResponse, EntityExtractionRequest,
    EntityExtractionResponse, TopicModelingRequest, TopicModelingResponse,
    BatchProcessRequest, BatchProcessResponse, ModelInfo
)

# Configure logging
logger = structlog.get_logger()

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
MODEL_CACHE_DIR = os.getenv("MODEL_CACHE_DIR", "./models")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Global variables
redis_client: Optional[redis.Redis] = None
sentiment_pipeline = None
emotion_pipeline = None
nlp_model = None
tokenizer = None
embedding_model = None

class MLService:
    def __init__(self):
        self.models_loaded = False
        self.model_info = {}
        
    async def load_models(self):
        """Load all ML models"""
        global sentiment_pipeline, emotion_pipeline, nlp_model, tokenizer, embedding_model
        
        logger.info("Loading ML models...")
        start_time = time.time()
        
        try:
            # Load sentiment analysis model
            logger.info("Loading sentiment analysis model...")
            sentiment_pipeline = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest",
                tokenizer="cardiffnlp/twitter-roberta-base-sentiment-latest",
                device=0 if DEVICE == "cuda" else -1,
                return_all_scores=True
            )
            
            # Load emotion detection model
            logger.info("Loading emotion detection model...")
            emotion_pipeline = pipeline(
                "text-classification",
                model="j-hartmann/emotion-english-distilroberta-base",
                device=0 if DEVICE == "cuda" else -1,
                return_all_scores=True
            )
            
            # Load spaCy model for NER
            logger.info("Loading spaCy model...")
            try:
                nlp_model = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("spaCy model not found, downloading...")
                os.system("python -m spacy download en_core_web_sm")
                nlp_model = spacy.load("en_core_web_sm")
            
            # Load embedding model for topic modeling
            logger.info("Loading embedding model...")
            tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
            embedding_model = AutoModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
            embedding_model.to(DEVICE)
            
            load_time = time.time() - start_time
            logger.info(f"All models loaded successfully in {load_time:.2f} seconds")
            
            # Store model information
            self.model_info = {
                "sentiment_model": "cardiffnlp/twitter-roberta-base-sentiment-latest",
                "emotion_model": "j-hartmann/emotion-english-distilroberta-base",
                "ner_model": "en_core_web_sm",
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                "device": DEVICE,
                "load_time": load_time,
                "loaded_at": datetime.utcnow().isoformat()
            }
            
            self.models_loaded = True
            
        except Exception as e:
            logger.error(f"Failed to load models: {str(e)}")
            raise e
    
    async def analyze_sentiment(self, text: str, language: str = "en") -> Dict[str, Any]:
        """Analyze sentiment of text"""
        if not self.models_loaded:
            raise HTTPException(status_code=503, detail="Models not loaded")
        
        start_time = time.time()
        
        try:
            # Preprocess text
            cleaned_text = self._preprocess_text(text)
            
            # Get sentiment scores
            sentiment_results = sentiment_pipeline(cleaned_text)
            
            # Process results
            scores = {}
            max_score = 0
            predicted_sentiment = "neutral"
            
            for result in sentiment_results[0]:
                label = result['label'].lower()
                score = result['score']
                
                # Map labels to standard format
                if label in ['label_2', 'positive']:
                    label = 'positive'
                elif label in ['label_0', 'negative']:
                    label = 'negative'
                elif label in ['label_1', 'neutral']:
                    label = 'neutral'
                
                scores[label] = score
                
                if score > max_score:
                    max_score = score
                    predicted_sentiment = label
            
            # Get emotion analysis
            emotion_results = emotion_pipeline(cleaned_text)
            emotions = {}
            for result in emotion_results[0]:
                emotions[result['label'].lower()] = result['score']
            
            processing_time = (time.time() - start_time) * 1000
            
            result = {
                "sentiment": predicted_sentiment,
                "confidence": max_score,
                "scores": scores,
                "emotions": emotions,
                "language_detected": language,
                "processing_time_ms": processing_time,
                "text_length": len(text),
                "cleaned_text_length": len(cleaned_text)
            }
            
            # Cache result
            await self._cache_result("sentiment", text, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Sentiment analysis failed: {str(e)}")
    
    async def extract_entities(self, text: str, language: str = "en") -> Dict[str, Any]:
        """Extract named entities from text"""
        if not self.models_loaded:
            raise HTTPException(status_code=503, detail="Models not loaded")
        
        start_time = time.time()
        
        try:
            # Process with spaCy
            doc = nlp_model(text)
            
            entities = []
            for ent in doc.ents:
                entities.append({
                    "text": ent.text,
                    "label": ent.label_,
                    "description": spacy.explain(ent.label_),
                    "start": ent.start_char,
                    "end": ent.end_char,
                    "confidence": float(ent._.get("confidence", 0.9))  # spaCy doesn't provide confidence by default
                })
            
            # Extract additional information
            tokens = [token.text for token in doc if not token.is_stop and not token.is_punct]
            pos_tags = [(token.text, token.pos_) for token in doc if not token.is_stop]
            
            # Extract hashtags and mentions
            hashtags = re.findall(r'#\w+', text)
            mentions = re.findall(r'@\w+', text)
            urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
            
            processing_time = (time.time() - start_time) * 1000
            
            result = {
                "entities": entities,
                "tokens": tokens[:50],  # Limit tokens
                "pos_tags": pos_tags[:50],  # Limit POS tags
                "hashtags": hashtags,
                "mentions": mentions,
                "urls": urls,
                "language_detected": language,
                "processing_time_ms": processing_time,
                "entity_count": len(entities)
            }
            
            # Cache result
            await self._cache_result("entities", text, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Entity extraction failed: {str(e)}")
    
    async def extract_topics(self, texts: List[str], num_topics: int = 5) -> Dict[str, Any]:
        """Extract topics from a collection of texts"""
        if not self.models_loaded:
            raise HTTPException(status_code=503, detail="Models not loaded")
        
        start_time = time.time()
        
        try:
            if len(texts) < 2:
                raise ValueError("Need at least 2 texts for topic modeling")
            
            # Preprocess texts
            cleaned_texts = [self._preprocess_text(text) for text in texts]
            
            # Create TF-IDF vectors
            vectorizer = TfidfVectorizer(
                max_features=1000,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=2,
                max_df=0.8
            )
            
            tfidf_matrix = vectorizer.fit_transform(cleaned_texts)
            
            # Perform clustering
            n_clusters = min(num_topics, len(texts) // 2)
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(tfidf_matrix)
            
            # Extract topics
            feature_names = vectorizer.get_feature_names_out()
            topics = []
            
            for i in range(n_clusters):
                # Get top terms for this cluster
                center = kmeans.cluster_centers_[i]
                top_indices = center.argsort()[-10:][::-1]
                top_terms = [feature_names[idx] for idx in top_indices]
                top_scores = [float(center[idx]) for idx in top_indices]
                
                # Get texts in this cluster
                cluster_texts = [texts[j] for j, cluster in enumerate(clusters) if cluster == i]
                
                topics.append({
                    "topic_id": i,
                    "terms": top_terms,
                    "scores": top_scores,
                    "document_count": len(cluster_texts),
                    "sample_texts": cluster_texts[:3]  # Sample texts
                })
            
            processing_time = (time.time() - start_time) * 1000
            
            result = {
                "topics": topics,
                "num_documents": len(texts),
                "num_topics": n_clusters,
                "processing_time_ms": processing_time,
                "cluster_assignments": clusters.tolist()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Topic extraction failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Topic extraction failed: {str(e)}")
    
    async def batch_process(self, texts: List[str], operations: List[str]) -> Dict[str, Any]:
        """Process multiple texts with multiple operations"""
        if not self.models_loaded:
            raise HTTPException(status_code=503, detail="Models not loaded")
        
        start_time = time.time()
        results = []
        
        try:
            for i, text in enumerate(texts):
                text_results = {"text_id": i, "original_text": text[:100] + "..." if len(text) > 100 else text}
                
                if "sentiment" in operations:
                    sentiment_result = await self.analyze_sentiment(text)
                    text_results["sentiment"] = sentiment_result
                
                if "entities" in operations:
                    entities_result = await self.extract_entities(text)
                    text_results["entities"] = entities_result
                
                results.append(text_results)
            
            # Topic modeling if requested and enough texts
            if "topics" in operations and len(texts) >= 2:
                topics_result = await self.extract_topics(texts)
                topic_info = topics_result
            else:
                topic_info = None
            
            processing_time = (time.time() - start_time) * 1000
            
            return {
                "results": results,
                "topics": topic_info,
                "total_texts": len(texts),
                "operations_performed": operations,
                "processing_time_ms": processing_time
            }
            
        except Exception as e:
            logger.error(f"Batch processing failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Batch processing failed: {str(e)}")
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for analysis"""
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove very short texts
        if len(text.strip()) < 3:
            return "neutral text"
        
        return text
    
    async def _cache_result(self, operation: str, text: str, result: Dict[str, Any]):
        """Cache analysis result in Redis"""
        try:
            # Create cache key
            text_hash = hash(text) % (10**8)  # Simple hash
            cache_key = f"ml_cache:{operation}:{text_hash}"
            
            # Store with expiration (1 hour)
            await redis_client.setex(
                cache_key, 
                3600, 
                json.dumps(result, default=str)
            )
        except Exception as e:
            logger.warning(f"Failed to cache result: {str(e)}")
    
    async def _get_cached_result(self, operation: str, text: str) -> Optional[Dict[str, Any]]:
        """Get cached analysis result"""
        try:
            text_hash = hash(text) % (10**8)
            cache_key = f"ml_cache:{operation}:{text_hash}"
            
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Failed to get cached result: {str(e)}")
        
        return None

# Initialize ML service
ml_service = MLService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global redis_client
    
    # Startup
    logger.info("Starting ML Service...")
    
    # Initialize Redis connection
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    await redis_client.ping()
    logger.info("Redis connection established")
    
    # Load ML models
    await ml_service.load_models()
    
    logger.info("ML Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ML Service...")
    if redis_client:
        await redis_client.close()
    logger.info("ML Service shutdown complete")

# Initialize FastAPI app
app = FastAPI(
    title="Social Media Analytics ML Service",
    description="Machine Learning service for NLP tasks including sentiment analysis and entity extraction",
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
        await redis_client.ping()
        
        return {
            "status": "healthy",
            "models_loaded": ml_service.models_loaded,
            "device": DEVICE,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unhealthy")

# Model information
@app.get("/models/info")
async def get_model_info():
    """Get information about loaded models"""
    return {
        "success": True,
        "data": ml_service.model_info,
        "models_loaded": ml_service.models_loaded
    }

# Sentiment analysis endpoint
@app.post("/sentiment")
async def analyze_sentiment_endpoint(request: SentimentRequest):
    """Analyze sentiment of text"""
    # Check cache first
    cached_result = await ml_service._get_cached_result("sentiment", request.text)
    if cached_result:
        return {
            "success": True,
            "data": cached_result,
            "cached": True
        }
    
    result = await ml_service.analyze_sentiment(request.text, request.language)
    return {
        "success": True,
        "data": result,
        "cached": False
    }

# Entity extraction endpoint
@app.post("/extract-entities")
async def extract_entities_endpoint(request: SentimentRequest):  # Reusing same model
    """Extract named entities from text"""
    # Check cache first
    cached_result = await ml_service._get_cached_result("entities", request.text)
    if cached_result:
        return {
            "success": True,
            "data": cached_result,
            "cached": True
        }
    
    result = await ml_service.extract_entities(request.text, request.language)
    return {
        "success": True,
        "data": result,
        "cached": False
    }

# Topic modeling endpoint
@app.post("/extract-topics")
async def extract_topics_endpoint(texts: List[str], num_topics: int = 5):
    """Extract topics from multiple texts"""
    result = await ml_service.extract_topics(texts, num_topics)
    return {
        "success": True,
        "data": result
    }

# Batch processing endpoint
@app.post("/batch-process")
async def batch_process_endpoint(texts: List[str], operations: List[str]):
    """Process multiple texts with multiple operations"""
    valid_operations = {"sentiment", "entities", "topics"}
    invalid_ops = set(operations) - valid_operations
    
    if invalid_ops:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid operations: {invalid_ops}. Valid: {valid_operations}"
        )
    
    result = await ml_service.batch_process(texts, operations)
    return {
        "success": True,
        "data": result
    }

# Cache management endpoints
@app.delete("/cache/clear")
async def clear_cache():
    """Clear ML cache"""
    try:
        keys = await redis_client.keys("ml_cache:*")
        if keys:
            await redis_client.delete(*keys)
        
        return {
            "success": True,
            "message": f"Cleared {len(keys)} cached results"
        }
    except Exception as e:
        logger.error(f"Failed to clear cache: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")

@app.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics"""
    try:
        keys = await redis_client.keys("ml_cache:*")
        
        stats = {
            "total_cached_results": len(keys),
            "cache_types": {},
            "memory_usage": await redis_client.memory_usage("ml_cache:*") if keys else 0
        }
        
        # Count by operation type
        for key in keys:
            operation = key.split(":")[1]
            stats["cache_types"][operation] = stats["cache_types"].get(operation, 0) + 1
        
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get cache stats")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)