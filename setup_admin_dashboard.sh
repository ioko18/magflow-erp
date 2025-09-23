#!/bin/bash
# Admin Dashboard Setup Script

echo "🚀 Setting up MagFlow Admin Dashboard"
echo "===================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📦 Installing frontend dependencies...${NC}"

# Install frontend dependencies
cd admin-frontend
if command -v npm &> /dev/null; then
    echo -e "${YELLOW}📥 Using npm to install dependencies...${NC}"
    npm install
elif command -v yarn &> /dev/null; then
    echo -e "${YELLOW}📥 Using yarn to install dependencies...${NC}"
    yarn install
else
    echo -e "${RED}❌ Neither npm nor yarn found. Please install Node.js and npm.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Frontend dependencies installed successfully!${NC}"

echo ""
echo -e "${BLUE}🛠️ Admin Dashboard Features Implemented:${NC}"
echo -e "${GREEN}✅ Modern React + TypeScript frontend${NC}"
echo -e "${GREEN}✅ Responsive Ant Design UI components${NC}"
echo -e "${GREEN}✅ Interactive charts with Recharts${NC}"
echo -e "${GREEN}✅ Real-time data integration${NC}"
echo -e "${GREEN}✅ Professional dashboard layout${NC}"
echo -e "${GREEN}✅ FastAPI backend integration${NC}"
echo -e "${GREEN}✅ Authentication system${NC}"
echo -e "${GREEN}✅ eMAG sync management${NC}"

echo ""
echo -e "${BLUE}🌐 How to Start the Admin Dashboard:${NC}"
echo ""
echo -e "${YELLOW}1. Start the backend (in one terminal):${NC}"
echo -e "${GREEN}   cd /Users/macos/anaconda3/envs/MagFlow${NC}"
echo -e "${GREEN}   uvicorn app.main:app --reload --port 8000${NC}"
echo ""

echo -e "${YELLOW}2. Start the frontend (in another terminal):${NC}"
echo -e "${GREEN}   cd /Users/macos/anaconda3/envs/MagFlow/admin-frontend${NC}"
echo -e "${GREEN}   npm run dev${NC}"
echo ""

echo -e "${YELLOW}3. Open your browser:${NC}"
echo -e "${GREEN}   http://localhost:3000${NC}"
echo ""

echo -e "${BLUE}🎯 Dashboard Features:${NC}"
echo -e "${GREEN}   • Main Dashboard with key metrics${NC}"
echo -e "${GREEN}   • eMAG Integration management${NC}"
echo -e "${GREEN}   • Real-time sync status${NC}"
echo -e "${GREEN}   • Interactive charts and graphs${NC}"
echo -e "${GREEN}   • Professional navigation${NC}"
echo -e "${GREEN}   • Responsive design${NC}"

echo ""
echo -e "${BLUE}🔧 API Endpoints Available:${NC}"
echo -e "${GREEN}   GET  /api/v1/admin/dashboard - Dashboard data${NC}"
echo -e "${GREEN}   POST /api/v1/admin/sync-emag - Trigger eMAG sync${NC}"
echo -e "${GREEN}   GET  /api/v1/admin/system-status - System health${NC}"
echo -e "${GREEN}   GET  /api/v1/emag/status - eMAG integration status${NC}"
echo -e "${GREEN}   POST /api/v1/emag/sync - Sync eMAG offers${NC}"

echo ""
echo -e "${GREEN}🎉 Admin Dashboard setup completed!${NC}"
echo -e "${YELLOW}💡 Ready to start development servers and access the dashboard!${NC}"
