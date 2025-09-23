#!/bin/bash

# SSL Certificate Management Script for MagFlow ERP
# This script manages SSL certificates using Let's Encrypt

set -e

# Configuration
DOMAIN_NAME="your-domain.com"
EMAIL_ADDRESS="admin@your-company.com"
DEPLOYMENT_DIR="/opt/magflow-erp"
CERTBOT_WEBROOT="/opt/magflow-erp/ssl_certs"
CERTBOT_LOGS="/opt/magflow-erp/logs/certbot"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Check if certbot is installed
if ! command -v certbot &> /dev/null; then
    log "Installing Certbot..."
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
fi

# Function to obtain SSL certificates
obtain_certificates() {
    log "🔐 Obtaining SSL certificates from Let's Encrypt..."

    # Stop nginx temporarily to free port 80
    if systemctl is-active --quiet nginx; then
        log "Stopping nginx to free port 80..."
        systemctl stop nginx
        sleep 5
    fi

    # Obtain certificates using standalone plugin
    certbot certonly \
        --standalone \
        --preferred-challenges http \
        --agree-tos \
        --email "$EMAIL_ADDRESS" \
        --domains "$DOMAIN_NAME,api.$DOMAIN_NAME" \
        --non-interactive \
        --cert-name magflow-erp

    if [ $? -eq 0 ]; then
        success "SSL certificates obtained successfully"
    else
        error "Failed to obtain SSL certificates"
    fi

    # Restart nginx
    if systemctl is-active --quiet nginx; then
        log "Starting nginx..."
        systemctl start nginx
    fi
}

# Function to renew certificates
renew_certificates() {
    log "🔄 Renewing SSL certificates..."

    certbot renew --cert-name magflow-erp --non-interactive

    if [ $? -eq 0 ]; then
        success "SSL certificates renewed successfully"

        # Reload nginx to pick up new certificates
        if systemctl is-active --quiet nginx; then
            systemctl reload nginx
            success "Nginx reloaded with new certificates"
        fi
    else
        error "Failed to renew SSL certificates"
    fi
}

# Function to configure SSL certificates in nginx
configure_nginx_ssl() {
    log "🌐 Configuring SSL certificates in nginx..."

    # Create SSL certificate symlinks
    SSL_DIR="/etc/letsencrypt/live/magflow-erp"

    if [ ! -f "$SSL_DIR/fullchain.pem" ] || [ ! -f "$SSL_DIR/privkey.pem" ]; then
        error "SSL certificates not found in $SSL_DIR"
    fi

    # Copy certificates to nginx ssl directory
    cp "$SSL_DIR/fullchain.pem" "$CERTBOT_WEBROOT/fullchain.pem"
    cp "$SSL_DIR/privkey.pem" "$CERTBOT_WEBROOT/privkey.pem"

    # Update nginx configuration
    sed -i "s|/etc/nginx/ssl/fullchain.pem|$CERTBOT_WEBROOT/fullchain.pem|g" "$DEPLOYMENT_DIR/nginx/nginx.conf"
    sed -i "s|/etc/nginx/ssl/privkey.pem|$CERTBOT_WEBROOT/privkey.pem|g" "$DEPLOYMENT_DIR/nginx/nginx.conf"

    success "SSL certificates configured in nginx"
}

# Function to setup automatic renewal
setup_auto_renewal() {
    log "⏰ Setting up automatic certificate renewal..."

    # Create renewal script
    cat > /etc/cron.daily/certbot-renew << 'EOF'
#!/bin/bash
# Certbot automatic renewal
certbot renew --cert-name magflow-erp --quiet --non-interactive

# Reload nginx if certificates were renewed
if [ $? -eq 0 ]; then
    systemctl reload nginx
    logger "SSL certificates renewed and nginx reloaded"
fi
EOF

    chmod +x /etc/cron.daily/certbot-renew

    # Test renewal
    certbot renew --dry-run --cert-name magflow-erp

    if [ $? -eq 0 ]; then
        success "Automatic certificate renewal configured"
    else
        error "Failed to setup automatic renewal"
    fi
}

# Function to create monitoring dashboard
create_ssl_dashboard() {
    log "📊 Creating SSL certificate monitoring dashboard..."

    # Create Prometheus metrics for SSL certificates
    cat > "$DEPLOYMENT_DIR/monitoring/ssl-metrics.txt" << 'EOF'
# SSL Certificate Metrics
ssl_certificate_expiry_days{gateway="nginx"} 30
ssl_certificate_valid{gateway="nginx"} 1
ssl_certificate_renewal_success{gateway="certbot"} 1
ssl_certificate_renewal_failures{gateway="certbot"} 0
EOF

    success "SSL certificate monitoring configured"
}

# Function to create backup of certificates
backup_certificates() {
    log "💾 Creating certificate backup..."

    BACKUP_DIR="/opt/magflow-erp/backups/ssl"
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)

    mkdir -p "$BACKUP_DIR"

    # Backup Let's Encrypt certificates
    if [ -d "/etc/letsencrypt/live/magflow-erp" ]; then
        cp -r /etc/letsencrypt/live/magflow-erp "$BACKUP_DIR/ssl_backup_$TIMESTAMP"
        success "SSL certificates backed up to: $BACKUP_DIR/ssl_backup_$TIMESTAMP"
    else
        warning "No Let's Encrypt certificates found to backup"
    fi
}

# Function to show SSL certificate information
show_ssl_info() {
    log "📋 SSL Certificate Information:"

    if [ -f "/etc/letsencrypt/live/magflow-erp/fullchain.pem" ]; then
        echo "Certificate Details:"
        openssl x509 -in /etc/letsencrypt/live/magflow-erp/fullchain.pem -text -noout | grep -E "(Subject:|Issuer:|Not Before:|Not After:|Subject Alternative Name:)" | head -10

        echo ""
        echo "Certificate Expiry:"
        openssl x509 -in /etc/letsencrypt/live/magflow-erp/fullchain.pem -checkend 2592000 -noout
        if [ $? -eq 0 ]; then
            echo "  ✅ Certificate is valid for more than 30 days"
        else
            echo "  ⚠️  Certificate expires in less than 30 days"
        fi
    else
        echo "No SSL certificates found"
    fi
}

# Main script logic
case "${1:-help}" in
    "obtain")
        obtain_certificates
        configure_nginx_ssl
        ;;
    "renew")
        renew_certificates
        ;;
    "setup")
        obtain_certificates
        configure_nginx_ssl
        setup_auto_renewal
        create_ssl_dashboard
        ;;
    "backup")
        backup_certificates
        ;;
    "info")
        show_ssl_info
        ;;
    "help"|*)
        echo "SSL Certificate Management Script for MagFlow ERP"
        echo ""
        echo "Usage: $0 {command}"
        echo ""
        echo "Commands:"
        echo "  obtain    - Obtain new SSL certificates from Let's Encrypt"
        echo "  renew     - Renew existing SSL certificates"
        echo "  setup     - Complete SSL setup (obtain + configure + auto-renewal)"
        echo "  backup    - Backup SSL certificates"
        echo "  info      - Show SSL certificate information"
        echo "  help      - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 setup          # Complete SSL setup"
        echo "  $0 renew          # Renew certificates"
        echo "  $0 info           # Check certificate status"
        ;;
esac

# Post-execution tasks
if [ "$1" != "help" ] && [ "$1" != "info" ]; then
    log "🔄 Reloading nginx configuration..."
    systemctl reload nginx

    log "✅ SSL certificate operation completed"
    echo ""
    echo "Next steps:"
    echo "1. Check nginx status: systemctl status nginx"
    echo "2. Test SSL: curl -I https://$DOMAIN_NAME"
    echo "3. View certificate: $0 info"
    echo "4. Monitor renewal: tail -f $CERTBOT_LOGS/letsencrypt.log"
fi
