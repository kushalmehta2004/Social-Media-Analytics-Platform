-- Social Media Analytics Database Schema
-- PostgreSQL with TimescaleDB for time-series data

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    is_admin BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Social media posts table (hypertable for time-series)
CREATE TABLE IF NOT EXISTS social_posts (
    post_id VARCHAR(255) PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    author VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Engagement metrics
    likes_count INTEGER DEFAULT 0,
    shares_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    retweets_count INTEGER DEFAULT 0,
    
    -- Metadata
    hashtags TEXT[], -- Array of hashtags
    mentions TEXT[], -- Array of mentions
    urls TEXT[], -- Array of URLs
    location VARCHAR(255),
    language VARCHAR(10),
    
    -- ML Analysis results
    sentiment VARCHAR(20),
    sentiment_confidence DECIMAL(5,4),
    sentiment_scores JSONB,
    emotions JSONB,
    entities JSONB,
    topics TEXT[],
    
    -- Processing metadata
    processed_at TIMESTAMP WITH TIME ZONE,
    processing_time_ms INTEGER,
    
    -- Indexes
    INDEX idx_platform (platform),
    INDEX idx_timestamp (timestamp),
    INDEX idx_author (author),
    INDEX idx_sentiment (sentiment),
    INDEX idx_hashtags USING GIN (hashtags),
    INDEX idx_mentions USING GIN (mentions),
    INDEX idx_entities USING GIN (entities),
    INDEX idx_topics USING GIN (topics)
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('social_posts', 'timestamp', if_not_exists => TRUE);

-- Trending topics table
CREATE TABLE IF NOT EXISTS trending_topics (
    id SERIAL PRIMARY KEY,
    topic VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    mentions_count INTEGER NOT NULL DEFAULT 0,
    sentiment_score DECIMAL(5,4) DEFAULT 0,
    growth_rate DECIMAL(8,4) DEFAULT 0,
    related_keywords TEXT[],
    time_window TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_topic (topic),
    INDEX idx_platform_trending (platform),
    INDEX idx_time_window (time_window),
    INDEX idx_mentions_count (mentions_count DESC),
    
    -- Unique constraint to prevent duplicates
    UNIQUE(topic, platform, time_window)
);

-- Convert trending topics to hypertable
SELECT create_hypertable('trending_topics', 'time_window', if_not_exists => TRUE);

-- User activity logs
CREATE TABLE IF NOT EXISTS user_activity (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    activity_type VARCHAR(50) NOT NULL,
    endpoint VARCHAR(255),
    request_data JSONB,
    response_status INTEGER,
    processing_time_ms INTEGER,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_user_activity (user_id),
    INDEX idx_activity_type (activity_type),
    INDEX idx_timestamp_activity (timestamp),
    INDEX idx_endpoint (endpoint)
);

-- Convert user activity to hypertable
SELECT create_hypertable('user_activity', 'timestamp', if_not_exists => TRUE);

-- Analytics aggregations table
CREATE TABLE IF NOT EXISTS analytics_aggregations (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    platform VARCHAR(50),
    time_bucket TIMESTAMP WITH TIME ZONE NOT NULL,
    bucket_size INTERVAL NOT NULL, -- '1 hour', '1 day', etc.
    value DECIMAL(15,4) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_metric_name (metric_name),
    INDEX idx_platform_analytics (platform),
    INDEX idx_time_bucket (time_bucket),
    INDEX idx_bucket_size (bucket_size),
    
    -- Unique constraint
    UNIQUE(metric_name, platform, time_bucket, bucket_size)
);

-- Convert analytics to hypertable
SELECT create_hypertable('analytics_aggregations', 'time_bucket', if_not_exists => TRUE);

-- System metrics table
CREATE TABLE IF NOT EXISTS system_metrics (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    value DECIMAL(15,4) NOT NULL,
    tags JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_service_name (service_name),
    INDEX idx_metric_name_system (metric_name),
    INDEX idx_timestamp_system (timestamp)
);

-- Convert system metrics to hypertable
SELECT create_hypertable('system_metrics', 'timestamp', if_not_exists => TRUE);

-- API rate limiting table
CREATE TABLE IF NOT EXISTS rate_limits (
    id SERIAL PRIMARY KEY,
    client_id VARCHAR(255) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    window_start TIMESTAMP WITH TIME ZONE NOT NULL,
    window_size INTERVAL NOT NULL,
    request_count INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_client_endpoint (client_id, endpoint),
    INDEX idx_window_start (window_start),
    
    -- Unique constraint
    UNIQUE(client_id, endpoint, window_start, window_size)
);

-- ML model performance tracking
CREATE TABLE IF NOT EXISTS ml_model_performance (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    operation VARCHAR(50) NOT NULL,
    input_length INTEGER,
    processing_time_ms INTEGER NOT NULL,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    confidence_score DECIMAL(5,4),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_model_name_perf (model_name),
    INDEX idx_operation_perf (operation),
    INDEX idx_timestamp_perf (timestamp),
    INDEX idx_success (success)
);

-- Convert ML performance to hypertable
SELECT create_hypertable('ml_model_performance', 'timestamp', if_not_exists => TRUE);

-- Create materialized views for common queries

-- Hourly sentiment aggregation
CREATE MATERIALIZED VIEW IF NOT EXISTS hourly_sentiment_stats AS
SELECT 
    time_bucket('1 hour', timestamp) AS hour,
    platform,
    sentiment,
    COUNT(*) as post_count,
    AVG(sentiment_confidence) as avg_confidence,
    AVG(likes_count + shares_count + comments_count) as avg_engagement
FROM social_posts 
WHERE processed_at IS NOT NULL
GROUP BY hour, platform, sentiment
ORDER BY hour DESC;

-- Daily trending topics
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_trending AS
SELECT 
    time_bucket('1 day', time_window) AS day,
    platform,
    topic,
    SUM(mentions_count) as total_mentions,
    AVG(sentiment_score) as avg_sentiment,
    MAX(growth_rate) as peak_growth_rate
FROM trending_topics
GROUP BY day, platform, topic
HAVING SUM(mentions_count) >= 10
ORDER BY day DESC, total_mentions DESC;

-- User engagement summary
CREATE MATERIALIZED VIEW IF NOT EXISTS user_engagement_summary AS
SELECT 
    u.user_id,
    u.username,
    COUNT(ua.id) as total_requests,
    COUNT(DISTINCT DATE(ua.timestamp)) as active_days,
    AVG(ua.processing_time_ms) as avg_response_time,
    MAX(ua.timestamp) as last_activity
FROM users u
LEFT JOIN user_activity ua ON u.user_id = ua.user_id
GROUP BY u.user_id, u.username;

-- Create functions for common operations

-- Function to get trending topics for a time period
CREATE OR REPLACE FUNCTION get_trending_topics(
    p_platform VARCHAR DEFAULT NULL,
    p_hours INTEGER DEFAULT 24,
    p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
    topic VARCHAR,
    mentions INTEGER,
    sentiment_score DECIMAL,
    growth_rate DECIMAL,
    platforms TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        tt.topic,
        SUM(tt.mentions_count)::INTEGER as mentions,
        AVG(tt.sentiment_score) as sentiment_score,
        AVG(tt.growth_rate) as growth_rate,
        ARRAY_AGG(DISTINCT tt.platform) as platforms
    FROM trending_topics tt
    WHERE tt.time_window >= NOW() - INTERVAL '1 hour' * p_hours
        AND (p_platform IS NULL OR tt.platform = p_platform)
    GROUP BY tt.topic
    ORDER BY mentions DESC, sentiment_score DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to get sentiment distribution
CREATE OR REPLACE FUNCTION get_sentiment_distribution(
    p_platform VARCHAR DEFAULT NULL,
    p_hours INTEGER DEFAULT 24
)
RETURNS TABLE (
    sentiment VARCHAR,
    count BIGINT,
    percentage DECIMAL
) AS $$
DECLARE
    total_count BIGINT;
BEGIN
    -- Get total count
    SELECT COUNT(*) INTO total_count
    FROM social_posts sp
    WHERE sp.timestamp >= NOW() - INTERVAL '1 hour' * p_hours
        AND (p_platform IS NULL OR sp.platform = p_platform)
        AND sp.sentiment IS NOT NULL;
    
    -- Return distribution
    RETURN QUERY
    SELECT 
        sp.sentiment,
        COUNT(*) as count,
        ROUND((COUNT(*)::DECIMAL / total_count * 100), 2) as percentage
    FROM social_posts sp
    WHERE sp.timestamp >= NOW() - INTERVAL '1 hour' * p_hours
        AND (p_platform IS NULL OR sp.platform = p_platform)
        AND sp.sentiment IS NOT NULL
    GROUP BY sp.sentiment
    ORDER BY count DESC;
END;
$$ LANGUAGE plpgsql;

-- Create indexes for performance
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_social_posts_composite 
ON social_posts (platform, timestamp DESC, sentiment);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_trending_composite 
ON trending_topics (platform, time_window DESC, mentions_count DESC);

-- Create triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create retention policies (TimescaleDB feature)
-- Keep detailed data for 30 days, then aggregate
SELECT add_retention_policy('social_posts', INTERVAL '30 days');
SELECT add_retention_policy('user_activity', INTERVAL '90 days');
SELECT add_retention_policy('system_metrics', INTERVAL '7 days');
SELECT add_retention_policy('ml_model_performance', INTERVAL '30 days');

-- Create continuous aggregates for real-time analytics
CREATE MATERIALIZED VIEW IF NOT EXISTS posts_per_hour
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', timestamp) AS bucket,
    platform,
    COUNT(*) as post_count,
    COUNT(CASE WHEN sentiment = 'positive' THEN 1 END) as positive_count,
    COUNT(CASE WHEN sentiment = 'negative' THEN 1 END) as negative_count,
    COUNT(CASE WHEN sentiment = 'neutral' THEN 1 END) as neutral_count
FROM social_posts
GROUP BY bucket, platform;

-- Add refresh policy for continuous aggregates
SELECT add_continuous_aggregate_policy('posts_per_hour',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');

-- Insert sample admin user (password: Admin123!)
INSERT INTO users (username, email, password_hash, full_name, is_admin) 
VALUES (
    'admin', 
    'admin@socialanalytics.com', 
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3bp.Gm.F5e', -- Admin123!
    'System Administrator', 
    TRUE
) ON CONFLICT (username) DO NOTHING;

-- Create sample data for testing (optional)
-- This will be populated by the data ingestion service

COMMIT;