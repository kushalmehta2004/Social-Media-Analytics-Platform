# 🚀 Social Media Analytics Platform - Setup Guide

This guide will help you set up and run the Real-time Social Media Analytics Platform on your local machine.

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Docker** (version 20.10+)
- **Docker Compose** (version 2.0+)
- **Python** (version 3.11+) - for setup script
- **Node.js** (version 18+) - for frontend development (optional)
- **Git** - for version control

### Windows Installation
```bash
# Install Docker Desktop from https://www.docker.com/products/docker-desktop
# Install Python from https://www.python.org/downloads/
# Install Node.js from https://nodejs.org/
```

### macOS Installation
```bash
# Install Docker Desktop from https://www.docker.com/products/docker-desktop
brew install python@3.11 node
```

### Linux Installation
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Python and Node.js
sudo apt update
sudo apt install python3.11 python3-pip nodejs npm
```

## 🚀 Quick Start (Automated Setup)

1. **Clone the repository:**
```bash
git clone <your-repository-url>
cd social-media-analytics
```

2. **Run the automated setup:**
```bash
python setup.py
```

The setup script will:
- Check all dependencies
- Create environment configuration
- Build Docker images
- Start all services
- Verify service health
- Display service URLs

3. **Access the platform:**
- Dashboard: http://localhost:3000
- API Documentation: http://localhost:8000/docs

## 🔧 Manual Setup

If you prefer to set up manually or the automated setup fails:

### Step 1: Environment Configuration

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Edit `.env` file with your configuration:
```bash
# Basic configuration (defaults work for local development)
DATABASE_URL=postgresql://analytics_user:analytics_pass@postgres:5432/social_analytics
REDIS_URL=redis://redis:6379
JWT_SECRET=your-super-secret-jwt-key-change-in-production

# Optional: Add real social media API keys
TWITTER_BEARER_TOKEN=your_twitter_bearer_token_here
```

### Step 2: Build and Start Services

1. **Build Docker images:**
```bash
docker-compose build
```

2. **Start all services:**
```bash
docker-compose up -d
```

3. **Check service status:**
```bash
docker-compose ps
```

### Step 3: Verify Installation

1. **Check service health:**
```bash
# API Gateway
curl http://localhost:8000/health

# ML Service
curl http://localhost:8001/health

# Analytics API
curl http://localhost:8002/health
```

2. **View logs:**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api-gateway
```

## 🌐 Service URLs

Once everything is running, you can access:

| Service | URL | Description |
|---------|-----|-------------|
| **Dashboard** | http://localhost:3000 | Main web interface |
| **API Gateway** | http://localhost:8000 | Central API endpoint |
| **API Documentation** | http://localhost:8000/docs | Interactive API docs |
| **ML Service** | http://localhost:8001 | NLP and sentiment analysis |
| **Analytics API** | http://localhost:8002 | Data analytics endpoints |
| **Grafana** | http://localhost:3001 | Monitoring dashboard (admin/admin) |
| **Prometheus** | http://localhost:9090 | Metrics collection |
| **PostgreSQL** | localhost:5432 | Database (analytics_user/analytics_pass) |
| **Redis** | localhost:6379 | Cache and message queue |

## 🧪 Testing the Platform

### 1. Dashboard Features
- Visit http://localhost:3000
- Explore real-time metrics
- View trending topics
- Analyze sentiment distribution

### 2. API Testing
- Go to http://localhost:8000/docs
- Try the sentiment analysis endpoint:
```json
POST /ml/sentiment
{
  "text": "I love this new product! It's amazing!",
  "language": "en"
}
```

### 3. Analytics Testing
- Check trending topics: `GET /analytics/trending`
- View sentiment overview: `GET /analytics/sentiment-overview`
- Get platform metrics: `GET /analytics/metrics`

## 🔧 Development Setup

For local development without Docker:

### Backend Services

1. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Start individual services:**
```bash
# API Gateway
cd services/api-gateway
uvicorn main:app --reload --port 8000

# ML Service
cd services/ml-service
uvicorn main:app --reload --port 8001

# Analytics API
cd services/analytics-api
uvicorn main:app --reload --port 8002
```

### Frontend Development

1. **Install dependencies:**
```bash
cd frontend
npm install
```

2. **Start development server:**
```bash
npm start
```

3. **Build for production:**
```bash
npm run build
```

## 📊 Data Generation

The platform includes a data ingestion service that generates realistic sample data:

- **Social media posts** with realistic content
- **Sentiment analysis** results
- **Trending topics** based on hashtags
- **User engagement** metrics

Data is generated continuously and stored in PostgreSQL with TimescaleDB for time-series optimization.

## 🛠️ Troubleshooting

### Common Issues

1. **Port conflicts:**
```bash
# Check what's using the ports
netstat -tulpn | grep :8000
# Kill the process or change ports in docker-compose.yml
```

2. **Docker build failures:**
```bash
# Clean Docker cache
docker system prune -a
# Rebuild without cache
docker-compose build --no-cache
```

3. **Database connection issues:**
```bash
# Check PostgreSQL logs
docker-compose logs postgres
# Reset database
docker-compose down -v
docker-compose up -d
```

4. **ML model loading issues:**
```bash
# Check ML service logs
docker-compose logs ml-service
# The first startup may take longer to download models
```

### Service-Specific Debugging

1. **API Gateway issues:**
```bash
docker-compose logs api-gateway
# Check Redis connection
docker-compose exec redis redis-cli ping
```

2. **ML Service issues:**
```bash
docker-compose logs ml-service
# Check if models are downloading
docker-compose exec ml-service ls -la /app/models
```

3. **Frontend issues:**
```bash
docker-compose logs frontend
# Check if API calls are working
curl http://localhost:8000/health
```

## 🔒 Security Notes

For production deployment:

1. **Change default passwords:**
   - Database credentials
   - JWT secret key
   - Grafana admin password

2. **Enable HTTPS:**
   - Use reverse proxy (nginx)
   - SSL certificates

3. **Network security:**
   - Firewall configuration
   - VPN access for admin interfaces

4. **API security:**
   - Rate limiting (already implemented)
   - API key authentication
   - Input validation

## 📈 Performance Optimization

1. **Database optimization:**
   - TimescaleDB is already configured
   - Indexes are created automatically
   - Consider partitioning for large datasets

2. **Caching:**
   - Redis caching is implemented
   - Adjust TTL values in service configs

3. **Scaling:**
   - Use Docker Swarm or Kubernetes
   - Load balancer for API Gateway
   - Read replicas for database

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

If you encounter issues:

1. Check the troubleshooting section
2. Review service logs
3. Create an issue on GitHub
4. Contact the development team

---

**Happy analyzing! 🎉**