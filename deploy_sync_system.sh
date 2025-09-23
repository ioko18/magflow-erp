#!/bin/bash
# MagFlow ERP - Enhanced Sync System Deployment Script
# This script deploys and starts the improved eMAG sync system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/opt/magflow"
SERVICE_NAME="sync-monitor"
LOG_DIR="/var/log/magflow"

echo -e "${BLUE}🚀 Deploying Enhanced MagFlow Sync System${NC}"
echo "=============================================="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ This script must be run as root${NC}"
   exit 1
fi

# Create directories
echo -e "${YELLOW}📁 Creating directories...${NC}"
mkdir -p "$LOG_DIR"
mkdir -p "$APP_DIR"
chown -R app:app "$LOG_DIR"
chown -R app:app "$APP_DIR"

# Copy files to deployment directory
echo -e "${YELLOW}📋 Copying sync files...${NC}"
if [[ -f "sync_emag_sync_improved.py" ]]; then
    cp sync_emag_sync_improved.py "$APP_DIR/"
    cp sync_monitor_recovery.py "$APP_DIR/"
    cp sync_monitor.service /etc/systemd/system/
    echo -e "${GREEN}✅ Sync files copied successfully${NC}"
else
    echo -e "${RED}❌ Sync files not found in current directory${NC}"
    exit 1
fi

# Set proper permissions
echo -e "${YELLOW}🔒 Setting permissions...${NC}"
chmod 644 "$APP_DIR/sync_emag_sync_improved.py"
chmod 644 "$APP_DIR/sync_monitor_recovery.py"
chmod 644 /etc/systemd/system/sync-monitor.service
chmod +x "$APP_DIR/sync_emag_sync_improved.py"

# Reload systemd daemon
echo -e "${YELLOW}🔄 Reloading systemd daemon...${NC}"
systemctl daemon-reload

# Stop existing service if running
echo -e "${YELLOW}🛑 Stopping existing sync monitor...${NC}"
systemctl stop "$SERVICE_NAME" 2>/dev/null || true
systemctl disable "$SERVICE_NAME" 2>/dev/null || true

# Enable and start the service
echo -e "${YELLOW}▶️  Starting enhanced sync monitor...${NC}"
systemctl enable "$SERVICE_NAME"
systemctl start "$SERVICE_NAME"

# Wait a moment and check status
sleep 3
echo -e "${YELLOW}📊 Checking service status...${NC}"
systemctl status "$SERVICE_NAME" --no-pager -l

# Check if service is running
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "${GREEN}✅ Sync Monitor service is running successfully${NC}"

    # Get service details
    echo ""
    echo -e "${BLUE}📈 Service Information:${NC}"
    echo "Service: $SERVICE_NAME"
    echo "Status: $(systemctl is-active "$SERVICE_NAME")"
    echo "Enabled: $(systemctl is-enabled "$SERVICE_NAME")"

    # Show recent logs
    echo ""
    echo -e "${BLUE}📜 Recent Logs:${NC}"
    journalctl -u "$SERVICE_NAME" --since "1 minute ago" --no-pager -n 10

    echo ""
    echo -e "${GREEN}🎉 Enhanced Sync System deployed successfully!${NC}"
    echo ""
    echo -e "${BLUE}📋 Next Steps:${NC}"
    echo "1. Monitor sync status: journalctl -u $SERVICE_NAME -f"
    echo "2. Check metrics: curl http://localhost:9108/metrics"
    echo "3. View sync health: python3 $APP_DIR/test_sync_improvements.py"
    echo "4. Manual sync test: python3 $APP_DIR/sync_emag_sync_improved.py"

else
    echo -e "${RED}❌ Sync Monitor service failed to start${NC}"
    echo ""
    echo -e "${YELLOW}🔍 Troubleshooting:${NC}"
    echo "1. Check logs: journalctl -u $SERVICE_NAME --no-pager -l"
    echo "2. Verify dependencies: systemctl status postgresql redis"
    echo "3. Check configuration: cat /etc/systemd/system/$SERVICE_NAME.service"
    echo "4. Test manually: cd $APP_DIR && python3 sync_monitor_recovery.py"
    exit 1
fi

echo ""
echo -e "${BLUE}🛠️  Useful Commands:${NC}"
echo "Start sync: systemctl start $SERVICE_NAME"
echo "Stop sync:  systemctl stop $SERVICE_NAME"
echo "Restart:    systemctl restart $SERVICE_NAME"
echo "View logs:  journalctl -u $SERVICE_NAME -f"
echo "Status:     systemctl status $SERVICE_NAME"
echo ""
echo -e "${GREEN}✅ Deployment completed!${NC}"
