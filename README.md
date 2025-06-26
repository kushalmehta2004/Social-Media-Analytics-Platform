# Real-time Social Media Analytics Platform

A comprehensive end-to-end platform for real-time social media data analysis, sentiment tracking, and trend detection.

## 🚀 Features

### Core Analytics
- **Real-time Data Ingestion**: Multi-platform social media data streaming
- **Advanced NLP Processing**: Sentiment analysis, entity extraction, topic modeling
- **Trend Detection**: Real-time trending topics and viral content identification
- **Influencer Analytics**: Authority scoring and network analysis

### Technical Highlights
- **Microservices Architecture**: Scalable, containerized services
- **Real-time Processing**: Apache Kafka + Redis for streaming data
- **ML Pipeline**: Custom sentiment models with continuous learning
- **Interactive Dashboard**: Real-time WebSocket-powered analytics dashboard
- **API Gateway**: Rate limiting, authentication, and request routing
- **Monitoring Stack**: Prometheus metrics + Grafana dashboards

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│   API Gateway    │───▶│  Auth Service   │
│ (Twitter, Reddit)│    │  (Rate Limiting) │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Stream Processor│◀───│   Message Queue  │───▶│ ML Service      │
│   (Kafka)       │    │   (Redis/Kafka)  │    │ (Sentiment/NLP) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Database      │    │  Analytics API   │    │  WebSocket      │
│ (PostgreSQL +   │    │    (FastAPI)     │    │   Service       │
│  TimescaleDB)   │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   Web Dashboard  │    │   Mobile API    │
                       │ (React/Vue + D3) │    │                 │
                       └──────────────────┘    └─────────────────┘
```

## 🛠️ Tech Stack

### Backend Services
- **Python 3.11+** - Core language
- **FastAPI** - High-performance API framework
- **Apache Kafka** - Real-time data streaming
- **Redis** - Caching and pub/sub
- **PostgreSQL + TimescaleDB** - Time-series data storage
- **Celery** - Distributed task processing

### Machine Learning
- **Transformers (Hugging Face)** - Pre-trained NLP models
- **scikit-learn** - Custom ML models
- **spaCy** - Advanced NLP processing
- **TensorFlow/PyTorch** - Deep learning models

### Frontend & Visualization
- **React/TypeScript** - Modern web dashboard
- **D3.js** - Advanced data visualizations
- **WebSocket** - Real-time updates
- **Tailwind CSS** - Modern styling

### Infrastructure
- **Docker & Docker Compose** - Containerization
- **Nginx** - Reverse proxy and load balancing
- **Prometheus + Grafana** - Monitoring and alerting
- **GitHub Actions** - CI/CD pipeline

## 🚦 Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+ (for frontend)

### Quick Start
```bash
# Clone and setup
git clone <repository>
cd social-media-analytics

# Start all services
docker-compose up -d

# Access the dashboard
open http://localhost:3000
```

## 📊 MVP Features

### Phase 1 (Current)
- [x] Basic data ingestion from Twitter API
- [x] Real-time sentiment analysis
- [x] Simple web dashboard
- [x] Docker containerization

### Phase 2 (Next)
- [ ] Multi-platform data sources (Reddit, Instagram)
- [ ] Advanced NLP (entity extraction, topic modeling)
- [ ] Real-time trending algorithms
- [ ] User authentication and multi-tenancy

### Phase 3 (Future)
- [ ] ML model training pipeline
- [ ] Advanced analytics (influencer scoring)
- [ ] Mobile app
- [ ] Cloud deployment (AWS/GCP)

## 🔧 Development

### Local Development
```bash
# Backend services
cd services/
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Start individual services
python -m uvicorn api_gateway.main:app --reload --port 8000
python -m uvicorn ml_service.main:app --reload --port 8001
python -m uvicorn analytics_api.main:app --reload --port 8002

# Frontend
cd frontend/
npm install
npm run dev
```

### Testing
```bash
# Backend tests
pytest tests/ -v

# Frontend tests
cd frontend/
npm test
```

## 📈 Monitoring

- **Application Metrics**: http://localhost:3001 (Grafana)
- **System Health**: http://localhost:9090 (Prometheus)
- **API Documentation**: http://localhost:8000/docs

## 🤝 Contributing

This is a portfolio project, but feedback and suggestions are welcome!


---

**Built with ❤️ to showcase modern Python development practices and real-time data processing capabilities.**
