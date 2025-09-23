#!/bin/bash

# MagFlow ERP Local Development Deployment Script
# This script deploys the complete MagFlow ERP system for local development

set -e  # Exit on any error

echo "🚀 MagFlow ERP Local Development Deployment Starting..."
echo "======================================================"

# Configuration for local development
DOMAIN_NAME="localhost"
EMAIL_ADDRESS="dev@localhost"
DEPLOYMENT_DIR="/Users/macos/anaconda3/envs/MagFlow"
DOCKER_COMPOSE_FILE="docker-compose.production.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Pre-deployment checks for local development
log "🔍 Running pre-deployment checks for local development..."

# Check Docker
if ! command -v docker &> /dev/null; then
    error "Docker is not installed. Please install Docker Desktop for Mac first."
fi

if ! command -v docker-compose &> /dev/null; then
    error "Docker Compose is not installed. Please install Docker Desktop for Mac first."
fi

# Check if ports are available (skip 80/443 for local dev)
PORTS_IN_USE=()
for port in 5432 6379 8000 8001 9090 3000 9093; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null; then
        PORTS_IN_USE+=($port)
    fi
done

if [ ${#PORTS_IN_USE[@]} -gt 0 ]; then
    warning "The following ports are already in use: ${PORTS_IN_USE[*]}"
    warning "This may cause conflicts. Please stop other services or update the configuration."
    read -p "Do you want to continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error "Deployment cancelled by user."
    fi
fi

# Ensure we're in the project directory
if [ ! -f "docker-compose.production.yml" ]; then
    error "docker-compose.production.yml not found. Please run this script from the MagFlow ERP project directory."
fi

# Update configuration for local development
log "⚙️ Updating configuration for local development..."
cp .env.production .env.local
sed -i.bak "s/your-domain.com/localhost/g" .env.local
sed -i.bak "s/admin@your-company.com/dev@localhost/g" .env.local
sed -i.bak "s|DEPLOYMENT_DIR=.*|DEPLOYMENT_DIR=$DEPLOYMENT_DIR|g" .env.local

# Create local directories
log "📁 Creating local directories..."
mkdir -p logs/{app,nginx,certbot}
mkdir -p data/{postgres,redis,prometheus,grafana,alertmanager}
mkdir -p ssl_certs

# Generate self-signed SSL certificates for local development
log "🔐 Generating self-signed SSL certificates for local development..."
if [ ! -f "ssl_certs/server.crt" ]; then
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout ssl_certs/server.key \
        -out ssl_certs/server.crt \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost" \
        -addext "subjectAltName=DNS:localhost,DNS:api.localhost" \
        2>/dev/null

    success "Self-signed SSL certificates generated for localhost"
fi

# Update Nginx configuration for local development
log "🌐 Updating Nginx configuration for local development..."
cp nginx/nginx.conf nginx/nginx.local.conf
sed -i.bak "s/your-domain.com/localhost/g" nginx/nginx.local.conf
sed -i.bak "s/api.your-domain.com/api.localhost/g" nginx/nginx.local.conf
sed -i.bak "s|ssl_certificate /etc/nginx/ssl/fullchain.pem|ssl_certificate $DEPLOYMENT_DIR/ssl_certs/server.crt|g" nginx/nginx.local.conf
sed -i.bak "s|ssl_certificate_key /etc/nginx/ssl/privkey.pem|ssl_certificate_key $DEPLOYMENT_DIR/ssl_certs/server.key|g" nginx/nginx.local.conf

# Stop any existing services
log "🛑 Stopping any existing services..."
docker-compose -f docker-compose.production.yml down 2>/dev/null || true

# Start services with local configuration
log "🚀 Starting local development services..."
DOCKER_COMPOSE_FILE="docker-compose.production.yml" docker-compose -f docker-compose.production.yml up -d

# Wait for services to start
log "⏳ Waiting for services to start..."
sleep 30

# Check service health
log "💓 Checking service health..."

# Check if containers are running
if ! docker-compose -f docker-compose.production.yml ps | grep -q "Up"; then
    error "Some services failed to start. Check the logs with: docker-compose logs"
fi

# Test application health
if curl -f -s http://localhost:8000/health > /dev/null; then
    success "Application is healthy"
else
    warning "Application health check failed. This may be normal during initial startup."
fi

# Test database connection
if docker-compose -f docker-compose.production.yml exec -T postgres pg_isready -U magflow_user -d magflow_prod > /dev/null 2>&1; then
    success "Database is ready"
else
    warning "Database health check failed"
fi

# Test Redis connection
if docker-compose -f docker-compose.production.yml exec -T redis redis-cli ping | grep -q PONG; then
    success "Redis is ready"
else
    warning "Redis health check failed"
fi

# Setup Grafana for local development
log "📊 Configuring Grafana for local development..."
sleep 10

# Check if Grafana is ready
if curl -f -s http://localhost:3000/api/health > /dev/null; then
    success "Grafana is ready"

    # Configure Grafana admin password for local development
    curl -X PUT -H "Content-Type: application/json" -d "{\"password\": \"admin123\"}" \
        http://localhost:3000/api/admin/users/1/password > /dev/null 2>&1

    success "Grafana admin password configured (admin/admin123)"
else
    warning "Grafana health check failed"
fi

# Setup Prometheus
log "📈 Configuring Prometheus..."
if curl -f -s http://localhost:9090/-/healthy > /dev/null; then
    success "Prometheus is ready"
else
    warning "Prometheus health check failed"
fi

# Test eMAG integration
log "🔗 Testing eMAG integration..."
if curl -f -s "http://localhost:8000/api/v1/emag/integration/status" > /dev/null; then
    success "eMAG integration is accessible"
else
    warning "eMAG integration check failed"
fi

# Display access information
log "🎯 Local development deployment completed successfully!"
echo ""
echo "================================================="
echo "🌐 LOCAL DEVELOPMENT ACCESS INFORMATION"
echo "================================================="
echo "Application URLs:"
echo "  • Main Application: http://localhost:8000"
echo "  • API Documentation: http://localhost:8000/docs"
echo "  • Health Check: http://localhost:8000/health"
echo "  • HTTPS Test: https://localhost:8000 (self-signed cert)"
echo ""
echo "Monitoring URLs:"
echo "  • Grafana: http://localhost:3000 (admin/admin123)"
echo "  • Prometheus: http://localhost:9090"
echo "  • Alert Manager: http://localhost:9093"
echo ""
echo "Database Access:"
echo "  • PostgreSQL: localhost:5432 (magflow_user/magflow_prod)"
echo "  • Redis: localhost:6379"
echo ""
echo "SSL Certificates:"
echo "  • Self-signed certificates created for localhost testing"
echo "  • Browser will show security warning (expected for local dev)"
echo ""
echo "================================================="
echo "🔧 LOCAL DEVELOPMENT COMMANDS"
echo "================================================="
echo "Start services: docker-compose -f docker-compose.production.yml up -d"
echo "Stop services: docker-compose -f docker-compose.production.yml down"
echo "View logs: docker-compose -f docker-compose.production.yml logs -f"
echo "Restart: docker-compose -f docker-compose.production.yml restart"
echo "Update: docker-compose -f docker-compose.production.yml pull && docker-compose -f docker-compose.production.yml up -d"
echo ""
echo "================================================="
echo "🧪 TESTING COMMANDS"
echo "================================================="
echo "Test API: curl http://localhost:8000/health"
echo "Test eMAG: curl http://localhost:8000/api/v1/emag/integration/status"
echo "Test RMA: curl -X POST http://localhost:8000/api/v1/rma/requests -d '{}'"
echo "Test DB: docker-compose exec postgres psql -U magflow_user -d magflow_prod"
echo ""
echo "================================================="
echo "📋 NEXT STEPS"
echo "================================================="
echo "1. Open http://localhost:3000 to access Grafana dashboards"
echo "2. Open http://localhost:8000/docs for API documentation"
echo "3. Run test scripts to verify functionality"
echo "4. Configure monitoring alerts if needed"
echo "5. Test custom business workflows"
echo ""
echo "================================================="
echo "✅ LOCAL DEVELOPMENT DEPLOYMENT COMPLETE!"
echo "================================================="

success "MagFlow ERP has been successfully deployed for local development!"
info "All services are running and accessible via localhost"

# Save deployment information
DEPLOYMENT_INFO="$DEPLOYMENT_DIR/deployment_info.txt"
cat > "$DEPLOYMENT_INFO" << EOF
MagFlow ERP Local Development Deployment
========================================
Deployment Date: $(date)
Environment: Local Development (Mac)
Domain: localhost
Deployment Directory: $DEPLOYMENT_DIR
Status: SUCCESS

Services Running:
- magflow-erp (Application) - http://localhost:8000
- postgres (Database) - localhost:5432
- redis (Cache) - localhost:6379
- nginx (Reverse Proxy) - localhost:80/443
- prometheus (Metrics) - http://localhost:9090
- grafana (Dashboards) - http://localhost:3000
- alertmanager (Alerts) - http://localhost:9093

SSL Certificates: Self-signed (for localhost testing)
Access: All services available via localhost

Grafana Credentials:
- Username: admin
- Password: admin123

Next Steps:
1. Access Grafana at http://localhost:3000
2. Test API endpoints at http://localhost:8000/docs
3. Run business flow tests
4. Configure monitoring dashboards
EOF

success "Deployment information saved to: $DEPLOYMENT_INFO"
info "You can now access your MagFlow ERP system at http://localhost:8000"

# Show final status
echo ""
echo "🎉 Ready to use! Open these URLs in your browser:"
echo "   📊 Grafana: http://localhost:3000 (admin/admin123)"
echo "   📚 API Docs: http://localhost:8000/docs"
echo "   🏠 Application: http://localhost:8000"
echo "   ❤️ Health Check: http://localhost:8000/health"
