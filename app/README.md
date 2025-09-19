# MagFlow ERP API

A modern, high-performance Enterprise Resource Planning API built with FastAPI, PostgreSQL, and Redis.

## 🚀 Features

- **JWT Authentication** - Secure token-based authentication with refresh tokens
- **Product Catalog** - Complete product management with categories and characteristics
- **VAT Calculation** - Automated VAT rate calculation for eMAG marketplace integration
- **Circuit Breaker** - Resilient external API calls with automatic failure handling
- **Rate Limiting** - Request throttling to prevent abuse
- **Health Monitoring** - Comprehensive health checks and metrics
- **Docker Support** - Containerized deployment with docker-compose
- **Observability** - OpenTelemetry integration for tracing and metrics

## 📋 Requirements

- Python 3.11+
- PostgreSQL 16+
- Redis 7+
- Docker & Docker Compose

## 🏃 Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/magflow.git
   cd magflow
   ```

2. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Run with Docker Compose**
   ```bash
   docker compose up -d
   ```

4. **Or run locally**
   ```bash
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

## 📖 API Documentation

Once running, visit:
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest -k health  # Health checks
pytest -k circuit_breaker  # Circuit breaker tests
pytest -k vat  # VAT calculation tests
```

## 🏗️ Architecture

### Core Components

- **API Layer** - FastAPI with automatic OpenAPI documentation
- **Authentication** - JWT tokens with refresh token rotation
- **Database** - PostgreSQL with SQLAlchemy ORM
- **Caching** - Redis for session storage and API response caching
- **External APIs** - Circuit breaker pattern for eMAG integration
- **Monitoring** - Health checks, metrics, and structured logging

### Key Patterns

- **Dependency Injection** - Clean architecture with service layers
- **Async/Await** - Full async support for high performance
- **Circuit Breaker** - Fault tolerance for external service calls
- **Repository Pattern** - Clean data access layer
- **Observer Pattern** - Event-driven architecture for metrics

## 🔒 Security

- Secure password hashing with bcrypt
- JWT token expiration and refresh
- CORS configuration for web clients
- Input validation and sanitization
- SQL injection prevention
- Rate limiting and abuse prevention

## 📊 Monitoring

- **Health Endpoints**:
  - `/health` - Overall system health
  - `/health/live` - Liveness probe
  - `/health/ready` - Readiness probe
  - `/health/startup` - Startup probe

- **Metrics**: Prometheus-compatible metrics at `/metrics`

- **Logging**: Structured JSON logging with correlation IDs

## 🚢 Deployment

### Docker Deployment

```bash
# Build and run
docker compose up -d

# View logs
docker compose logs -f

# Scale services
docker compose up -d --scale app=3
```

### Production Deployment

The application is production-ready with:
- Health checks for load balancers
- Graceful shutdown handling
- Connection pooling
- Metrics collection
- Security headers

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is proprietary software. See LICENSE file for details.

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Contact the development team
- Check the documentation at /docs

---

**Built with ❤️ using FastAPI, PostgreSQL, and Redis**

