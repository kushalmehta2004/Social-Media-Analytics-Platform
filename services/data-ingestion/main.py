"""
Data Ingestion Service
Simulates social media data ingestion and processing
"""

import asyncio
import asyncpg
import redis.asyncio as redis
import httpx
import json
import os
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import structlog
import uuid

# Configure logging
logger = structlog.get_logger()

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://analytics_user:analytics_pass@localhost:5432/social_analytics")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://localhost:8001")

class DataIngestionService:
    def __init__(self):
        self.db_pool = None
        self.redis_client = None
        self.http_client = None
        self.running = False
        
    async def initialize(self):
        """Initialize connections"""
        logger.info("Initializing Data Ingestion Service...")
        
        # Database connection
        self.db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
        logger.info("Database connection pool created")
        
        # Redis connection
        self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        await self.redis_client.ping()
        logger.info("Redis connection established")
        
        # HTTP client for ML service
        self.http_client = httpx.AsyncClient(timeout=30.0)
        logger.info("HTTP client initialized")
        
        logger.info("Data Ingestion Service initialized successfully")
    
    async def cleanup(self):
        """Cleanup connections"""
        logger.info("Cleaning up Data Ingestion Service...")
        
        if self.http_client:
            await self.http_client.aclose()
        if self.db_pool:
            await self.db_pool.close()
        if self.redis_client:
            await self.redis_client.close()
            
        logger.info("Data Ingestion Service cleanup complete")
    
    def generate_sample_post(self) -> Dict[str, Any]:
        """Generate a sample social media post"""
        platforms = ["twitter", "reddit", "instagram"]
        platform = random.choice(platforms)
        
        # Sample content templates
        content_templates = [
            "Just tried the new {product} and it's {sentiment_word}! {hashtag}",
            "Can't believe how {sentiment_word} this {topic} is! Anyone else feel the same?",
            "Breaking: {topic} just announced {news}. This is {sentiment_word}!",
            "My thoughts on {topic}: it's absolutely {sentiment_word}. {hashtag}",
            "Why is everyone talking about {topic}? It seems {sentiment_word} to me.",
            "Update on {topic}: things are looking {sentiment_word} now {hashtag}",
            "Just saw the news about {topic}. Feeling {sentiment_word} about this.",
            "Hot take: {topic} is {sentiment_word} and here's why...",
            "Can we talk about how {sentiment_word} {topic} has become?",
            "Unpopular opinion: {topic} is actually {sentiment_word} {hashtag}"
        ]
        
        # Sample data
        products = ["iPhone 15", "Tesla Model Y", "ChatGPT", "Netflix", "Spotify", "Amazon Prime"]
        topics = ["climate change", "AI technology", "cryptocurrency", "remote work", "social media", "electric vehicles"]
        news_items = ["major update", "price change", "new feature", "partnership deal", "policy change"]
        
        positive_words = ["amazing", "fantastic", "incredible", "outstanding", "brilliant", "wonderful"]
        negative_words = ["terrible", "awful", "disappointing", "frustrating", "horrible", "annoying"]
        neutral_words = ["okay", "decent", "average", "normal", "standard", "typical"]
        
        # Randomly choose sentiment and corresponding words
        sentiment_choice = random.choices(
            ["positive", "negative", "neutral"], 
            weights=[0.4, 0.3, 0.3]
        )[0]
        
        if sentiment_choice == "positive":
            sentiment_words = positive_words
        elif sentiment_choice == "negative":
            sentiment_words = negative_words
        else:
            sentiment_words = neutral_words
        
        # Generate content
        template = random.choice(content_templates)
        content = template.format(
            product=random.choice(products),
            topic=random.choice(topics),
            news=random.choice(news_items),
            sentiment_word=random.choice(sentiment_words),
            hashtag=f"#{random.choice(topics).replace(' ', '')}"
        )
        
        # Generate engagement metrics (realistic distributions)
        if platform == "twitter":
            likes = random.randint(0, 1000)
            shares = random.randint(0, likes // 3)
            comments = random.randint(0, likes // 5)
        elif platform == "reddit":
            likes = random.randint(0, 500)  # upvotes
            shares = 0  # Reddit doesn't have shares
            comments = random.randint(0, likes // 2)
        else:  # instagram
            likes = random.randint(0, 2000)
            shares = 0  # Instagram stories/DMs
            comments = random.randint(0, likes // 10)
        
        # Extract hashtags and mentions
        hashtags = [word[1:] for word in content.split() if word.startswith('#')]
        mentions = [word[1:] for word in content.split() if word.startswith('@')]
        
        return {
            "post_id": f"{platform}_{uuid.uuid4().hex[:12]}",
            "platform": platform,
            "author": f"user_{random.randint(1000, 9999)}",
            "content": content,
            "timestamp": datetime.utcnow() - timedelta(minutes=random.randint(0, 60)),
            "likes_count": likes,
            "shares_count": shares,
            "comments_count": comments,
            "retweets_count": shares if platform == "twitter" else 0,
            "hashtags": hashtags,
            "mentions": mentions,
            "urls": [],
            "location": random.choice([None, "New York", "London", "Tokyo", "San Francisco"]),
            "language": "en"
        }
    
    async def process_with_ml(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """Process post with ML service"""
        try:
            # Analyze sentiment
            sentiment_response = await self.http_client.post(
                f"{ML_SERVICE_URL}/sentiment",
                json={"text": post["content"], "language": post.get("language", "en")}
            )
            
            if sentiment_response.status_code == 200:
                sentiment_data = sentiment_response.json()["data"]
                post.update({
                    "sentiment": sentiment_data["sentiment"],
                    "sentiment_confidence": sentiment_data["confidence"],
                    "sentiment_scores": sentiment_data["scores"],
                    "emotions": sentiment_data.get("emotions", {}),
                    "processing_time_ms": int(sentiment_data["processing_time_ms"])
                })
            
            # Extract entities
            entities_response = await self.http_client.post(
                f"{ML_SERVICE_URL}/extract-entities",
                json={"text": post["content"], "language": post.get("language", "en")}
            )
            
            if entities_response.status_code == 200:
                entities_data = entities_response.json()["data"]
                post["entities"] = entities_data["entities"]
                
                # Extract topics from entities
                topics = []
                for entity in entities_data["entities"]:
                    if entity["label"] in ["ORG", "PRODUCT", "EVENT", "PERSON"]:
                        topics.append(entity["text"].lower())
                post["topics"] = list(set(topics))  # Remove duplicates
            
            post["processed_at"] = datetime.utcnow()
            
        except Exception as e:
            logger.warning(f"ML processing failed for post {post['post_id']}: {str(e)}")
            # Set default values if ML processing fails
            post.update({
                "sentiment": "neutral",
                "sentiment_confidence": 0.5,
                "sentiment_scores": {"positive": 0.33, "negative": 0.33, "neutral": 0.34},
                "emotions": {},
                "entities": [],
                "topics": [],
                "processed_at": datetime.utcnow(),
                "processing_time_ms": 0
            })
        
        return post
    
    async def store_post(self, post: Dict[str, Any]):
        """Store post in database"""
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                INSERT INTO social_posts (
                    post_id, platform, author, content, timestamp,
                    likes_count, shares_count, comments_count, retweets_count,
                    hashtags, mentions, urls, location, language,
                    sentiment, sentiment_confidence, sentiment_scores, emotions,
                    entities, topics, processed_at, processing_time_ms
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
                    $15, $16, $17, $18, $19, $20, $21, $22
                ) ON CONFLICT (post_id) DO NOTHING
                """
                
                await conn.execute(
                    query,
                    post["post_id"], post["platform"], post["author"], post["content"],
                    post["timestamp"], post["likes_count"], post["shares_count"],
                    post["comments_count"], post["retweets_count"], post["hashtags"],
                    post["mentions"], post["urls"], post["location"], post["language"],
                    post["sentiment"], post["sentiment_confidence"],
                    json.dumps(post["sentiment_scores"]), json.dumps(post["emotions"]),
                    json.dumps(post["entities"]), post["topics"], post["processed_at"],
                    post["processing_time_ms"]
                )
                
        except Exception as e:
            logger.error(f"Failed to store post {post['post_id']}: {str(e)}")
    
    async def update_trending_topics(self):
        """Update trending topics based on recent posts"""
        try:
            async with self.db_pool.acquire() as conn:
                # Get trending hashtags from last hour
                query = """
                SELECT 
                    unnest(hashtags) as topic,
                    platform,
                    COUNT(*) as mentions_count,
                    AVG(CASE 
                        WHEN sentiment = 'positive' THEN 1
                        WHEN sentiment = 'negative' THEN -1
                        ELSE 0
                    END) as sentiment_score
                FROM social_posts 
                WHERE timestamp >= NOW() - INTERVAL '1 hour'
                    AND hashtags IS NOT NULL
                    AND array_length(hashtags, 1) > 0
                GROUP BY topic, platform
                HAVING COUNT(*) >= 3
                ORDER BY mentions_count DESC
                LIMIT 20
                """
                
                rows = await conn.fetch(query)
                
                current_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
                
                for row in rows:
                    # Calculate growth rate (simplified)
                    growth_rate = random.uniform(0.1, 2.0)  # Placeholder
                    
                    # Insert or update trending topic
                    insert_query = """
                    INSERT INTO trending_topics (
                        topic, platform, mentions_count, sentiment_score, 
                        growth_rate, related_keywords, time_window
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (topic, platform, time_window) 
                    DO UPDATE SET 
                        mentions_count = EXCLUDED.mentions_count,
                        sentiment_score = EXCLUDED.sentiment_score,
                        growth_rate = EXCLUDED.growth_rate
                    """
                    
                    await conn.execute(
                        insert_query,
                        row["topic"], row["platform"], row["mentions_count"],
                        float(row["sentiment_score"]), growth_rate,
                        [], current_time
                    )
                
                logger.info(f"Updated {len(rows)} trending topics")
                
        except Exception as e:
            logger.error(f"Failed to update trending topics: {str(e)}")
    
    async def update_realtime_stats(self):
        """Update real-time statistics in Redis"""
        try:
            async with self.db_pool.acquire() as conn:
                # Get current stats
                query = """
                SELECT 
                    COUNT(*) as posts_today,
                    COUNT(DISTINCT author) as active_users,
                    COUNT(CASE WHEN sentiment = 'positive' THEN 1 END) as positive,
                    COUNT(CASE WHEN sentiment = 'negative' THEN 1 END) as negative,
                    COUNT(CASE WHEN sentiment = 'neutral' THEN 1 END) as neutral,
                    COUNT(DISTINCT unnest(hashtags)) as trending_topics
                FROM social_posts 
                WHERE timestamp >= CURRENT_DATE
                """
                
                row = await conn.fetchrow(query)
                
                stats = {
                    "active_users": row["active_users"],
                    "posts_processed_today": row["posts_today"],
                    "sentiment_distribution": {
                        "positive": row["positive"],
                        "negative": row["negative"],
                        "neutral": row["neutral"]
                    },
                    "trending_topics_count": row["trending_topics"],
                    "last_updated": datetime.utcnow().isoformat()
                }
                
                # Store in Redis
                await self.redis_client.setex(
                    "realtime:stats", 
                    60,  # 1 minute expiry
                    json.dumps(stats, default=str)
                )
                
        except Exception as e:
            logger.error(f"Failed to update realtime stats: {str(e)}")
    
    async def run_ingestion_loop(self):
        """Main ingestion loop"""
        logger.info("Starting data ingestion loop...")
        self.running = True
        
        while self.running:
            try:
                # Generate and process posts
                batch_size = random.randint(1, 5)  # Variable batch size
                posts = []
                
                for _ in range(batch_size):
                    post = self.generate_sample_post()
                    processed_post = await self.process_with_ml(post)
                    posts.append(processed_post)
                
                # Store posts
                for post in posts:
                    await self.store_post(post)
                
                logger.info(f"Processed and stored {len(posts)} posts")
                
                # Update trending topics every 10 iterations
                if random.randint(1, 10) == 1:
                    await self.update_trending_topics()
                
                # Update real-time stats
                await self.update_realtime_stats()
                
                # Wait before next batch (10-30 seconds)
                await asyncio.sleep(random.randint(10, 30))
                
            except Exception as e:
                logger.error(f"Error in ingestion loop: {str(e)}")
                await asyncio.sleep(5)  # Short wait before retrying
    
    async def stop(self):
        """Stop the ingestion service"""
        logger.info("Stopping data ingestion...")
        self.running = False

async def main():
    """Main function"""
    service = DataIngestionService()
    
    try:
        await service.initialize()
        await service.run_ingestion_loop()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Service error: {str(e)}")
    finally:
        await service.stop()
        await service.cleanup()

if __name__ == "__main__":
    asyncio.run(main())