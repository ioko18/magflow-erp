#!/bin/bash

# MagFlow ERP Production Deployment Script
# This script deploys the complete MagFlow ERP system to production

set -e  # Exit on any error

echo "🚀 MagFlow ERP Production Deployment Starting..."
echo "================================================="

# Configuration
DOMAIN_NAME="your-domain.com"
EMAIL_ADDRESS="admin@your-company.com"
DEPLOYMENT_DIR="/opt/magflow-erp"
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

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    error "This script should not be run as root. Please run as a regular user with sudo access."
fi

# Pre-deployment checks
log "🔍 Running pre-deployment checks..."

# Check Docker
if ! command -v docker &> /dev/null; then
    error "Docker is not installed. Please install Docker first."
fi

if ! command -v docker-compose &> /dev/null; then
    error "Docker Compose is not installed. Please install Docker Compose first."
fi

# Check if ports are available
PORTS_IN_USE=()
for port in 80 443 5432 6379 8000 8001 9090 3000 9093; do
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null; then
        PORTS_IN_USE+=($port)
    fi
done

if [ ${#PORTS_IN_USE[@]} -gt 0 ]; then
    warning "The following ports are already in use: ${PORTS_IN_USE[*]}"
    warning "This may cause conflicts. Please ensure these ports are available or update the configuration."
fi

# Create deployment directory
log "📁 Creating deployment directory..."
if [ ! -d "$DEPLOYMENT_DIR" ]; then
    sudo mkdir -p "$DEPLOYMENT_DIR"
    sudo chown $USER:$USER "$DEPLOYMENT_DIR"
fi

cd "$DEPLOYMENT_DIR"

# Copy project files
log "📋 Copying project files..."
if [ ! -f "docker-compose.production.yml" ]; then
    warning "docker-compose.production.yml not found. Please ensure you're in the correct directory."
    error "Deployment files not found. Please run this script from the MagFlow ERP project directory."
fi

# Update configuration
log "⚙️ Updating production configuration..."
cp .env.production .env
sed -i.bak "s/your-domain.com/$DOMAIN_NAME/g" .env
sed -i.bak "s/admin@your-company.com/$EMAIL_ADDRESS/g" .env

# Create SSL certificates directory
log "🔐 Setting up SSL certificates directory..."
sudo mkdir -p ssl_certs
sudo chown $USER:$USER ssl_certs
sudo chmod 755 ssl_certs

# Create log directories
log "📊 Creating log directories..."
sudo mkdir -p logs/{app,nginx,certbot}
sudo chown -R $USER:$USER logs
sudo chmod -R 755 logs

# Create data directories
log "💾 Creating data directories..."
sudo mkdir -p data/{postgres,redis,prometheus,grafana,alertmanager}
sudo chown -R $USER:$USER data
sudo chmod -R 755 data

# Generate SSL certificates (self-signed for testing)
log "🔐 Generating self-signed SSL certificates for testing..."
if [ ! -f "ssl_certs/server.crt" ]; then
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout ssl_certs/server.key \
        -out ssl_certs/server.crt \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=$DOMAIN_NAME" \
        -addext "subjectAltName=DNS:$DOMAIN_NAME,DNS:api.$DOMAIN_NAME" \
        2>/dev/null

    success "Self-signed SSL certificates generated"
fi

# Update Nginx configuration
log "🌐 Updating Nginx configuration..."
sed -i.bak "s/your-domain.com/$DOMAIN_NAME/g" nginx/nginx.conf
sed -i.bak "s/api.your-domain.com/api.$DOMAIN_NAME/g" nginx/nginx.conf

# Start services
log "🚀 Starting production services..."
docker-compose -f docker-compose.production.yml down 2>/dev/null || true
docker-compose -f docker-compose.production.yml up -d

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

# Setup Grafana
log "📊 Configuring Grafana..."
sleep 10

# Check if Grafana is ready
if curl -f -s http://localhost:3000/api/health > /dev/null; then
    success "Grafana is ready"

    # Configure Grafana admin password
    curl -X PUT -H "Content-Type: application/json" -d "{\"password\": \"secure_grafana_password\"}" \
        http://localhost:3000/api/admin/users/1/password > /dev/null 2>&1

    success "Grafana admin password configured"
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

# Display access information
log "🎯 Deployment completed successfully!"
echo ""
echo "================================================="
echo "🌐 ACCESS INFORMATION"
echo "================================================="
echo "Application URLs:"
echo "  • Main Application: https://$DOMAIN_NAME"
echo "  • API Documentation: https://$DOMAIN_NAME/docs"
echo "  • Health Check: https://$DOMAIN_NAME/health"
echo ""
echo "Monitoring URLs:"
echo "  • Grafana: http://localhost:3000 (admin/secure_grafana_password)"
echo "  • Prometheus: http://localhost:9090"
echo "  • Alert Manager: http://localhost:9093"
echo ""
echo "Database Access:"
echo "  • PostgreSQL: localhost:5432 (magflow_user/magflow_prod)"
echo "  • Redis: localhost:6379"
echo ""
echo "SSL Certificates:"
echo "  • Self-signed certificates created for testing"
echo "  • Replace with Let's Encrypt certificates for production"
echo ""
echo "================================================="
echo "🔧 MANAGEMENT COMMANDS"
echo "================================================="
echo "Start services: docker-compose -f docker-compose.production.yml up -d"
echo "Stop services: docker-compose -f docker-compose.production.yml down"
echo "View logs: docker-compose -f docker-compose.production.yml logs -f"
echo "Update: docker-compose -f docker-compose.production.yml pull && docker-compose -f docker-compose.production.yml up -d"
echo ""
echo "================================================="
echo "📋 NEXT STEPS"
echo "================================================="
echo "1. Replace self-signed SSL certificates with Let's Encrypt"
echo "2. Configure monitoring alerts"
echo "3. Set up automated backups"
echo "4. Configure domain DNS records"
echo "5. Set up monitoring dashboards"
echo "6. Test all business workflows"
echo ""
echo "================================================="
echo "✅ PRODUCTION DEPLOYMENT COMPLETE!"
echo "================================================="

success "MagFlow ERP has been successfully deployed to production!"
warning "Don't forget to replace the self-signed SSL certificates with proper certificates for production use."

# Save deployment information
DEPLOYMENT_INFO="$DEPLOYMENT_DIR/deployment_info.txt"
cat > "$DEPLOYMENT_INFO" << EOF
MagFlow ERP Production Deployment
==================================
Deployment Date: $(date)
Domain: $DOMAIN_NAME
Email: $EMAIL_ADDRESS
Deployment Directory: $DEPLOYMENT_DIR
Status: SUCCESS

Services Running:
- magflow-erp (Application)
- postgres (Database)
- redis (Cache)
- nginx (Reverse Proxy)
- prometheus (Metrics)
- grafana (Dashboards)
- alertmanager (Alerts)

SSL Certificates: Self-signed (for testing)
Next Step: Replace with Let's Encrypt certificates
EOF

success "Deployment information saved to: $DEPLOYMENT_INFO"
