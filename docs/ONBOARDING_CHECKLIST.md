# MagFlow Onboarding Checklist

## Prerequisites

- [ ] Docker and Docker Compose installed
- [ ] Git installed and configured
- [ ] Python 3.11+ installed
- [ ] Access to the repository
- [ ] Required environment variables set in `.env` file

## Initial Setup

### 1. Repository Setup

- [ ] Clone the repository
  ```bash
  git clone <repository-url>
  cd magflow
  ```
- [ ] Set up git hooks
  ```bash
  pre-commit install
  ```
- [ ] Create and configure `.env` file
  ```bash
  cp .env.example .env
  # Update values as needed
  ```

### 2. Docker Setup

- [ ] Build and start containers
  ```bash
  docker compose up -d --build
  ```
- [ ] Verify all services are running
  ```bash
  docker compose ps
  ```
- [ ] Check service logs for any errors
  ```bash
  docker compose logs -f
  ```

### 3. Database Setup

- [ ] Run database migrations
  ```bash
  docker compose exec app alembic upgrade head
  ```
- [ ] Verify database connection
  ```bash
  docker compose exec db psql -U postgres -d magflow -c "SELECT 1"
  ```
- [ ] Check PgBouncer connection
  ```bash
  docker compose exec pgbouncer psql -h localhost -p 6432 -U app -d magflow -c "SELECT 1"
  ```

## Development Environment

### 1. Python Environment

- [ ] Set up Python virtual environment
  ```bash
  python -m venv venv
  source venv/bin/activate  # On Windows: .\venv\Scripts\activate
  ```
- [ ] Install dependencies
  ```bash
  pip install -r requirements.txt
  ```
- [ ] Install development dependencies
  ```bash
  pip install -r requirements-dev.txt
  ```

### 2. Code Quality

- [ ] Run linters
  ```bash
  make lint
  ```
- [ ] Run type checking
  ```bash
  make typecheck
  ```
- [ ] Run tests
  ```bash
  make test
  ```

## Application Verification

### 1. API Endpoints

- [ ] Health check
  ```bash
  curl http://localhost:8000/health
  ```
- [ ] API documentation
  - Swagger UI: http://localhost:8000/docs
  - ReDoc: http://localhost:8000/redoc

### 2. Authentication

- [ ] Generate JWT keys (if not exists)
  ```bash
  ./scripts/generate-jwt-keys.sh
  ```
- [ ] Test authentication
  ```bash
  # Get access token
  curl -X POST http://localhost:8000/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"test@example.com","password":"password"}'
  ```

## Documentation

- [ ] Review architecture documentation
- [ ] Check API documentation
- [ ] Read security guidelines
- [ ] Review deployment procedures

## Common Issues

### Database Connection Issues

- [ ] Check if PostgreSQL is running
- [ ] Verify PgBouncer configuration
- [ ] Check connection strings in `.env`

### JWT Issues

- [ ] Verify JWT keys exist and are readable
- [ ] Check token expiration
- [ ] Validate token claims

### Performance Issues

- [ ] Check database connection pool
- [ ] Monitor resource usage
- [ ] Review slow queries

## Security Checklist

- [ ] Change default credentials
- [ ] Enable 2FA for repository access
- [ ] Review access controls
- [ ] Verify TLS configuration

## Post-Setup

- [ ] Run full test suite
- [ ] Perform load testing
- [ ] Verify backup procedures
- [ ] Document any issues found

## Support

For assistance, contact:

- **Development Team**: dev@example.com
- **Infrastructure**: infra@example.com
- **Security**: security@example.com

______________________________________________________________________

*Last Updated: 2023-05-15*
*Version: 1.0.0*
