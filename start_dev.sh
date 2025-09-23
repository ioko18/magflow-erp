#!/bin/bash
# Start Development Environment Script

echo "🚀 Starting MagFlow Development Environment"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}📋 Checking environment...${NC}"

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python not found. Please ensure Python is installed.${NC}"
    exit 1
fi

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js not found. Please install Node.js to run the admin dashboard.${NC}"
    echo -e "${YELLOW}💡 Download from: https://nodejs.org/${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Environment check passed${NC}"
echo ""

# Function to start backend
start_backend() {
    echo -e "${BLUE}🐍 Starting FastAPI Backend...${NC}"
    echo -e "${YELLOW}   URL: http://localhost:8000${NC}"
    echo -e "${YELLOW}   API Docs: http://localhost:8000/docs${NC}"
    echo -e "${YELLOW}   Admin: http://localhost:8000/admin${NC}"
    echo ""

    # Export environment variables
    export $(grep -v '^#' .env | xargs)

    # Start FastAPI server
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

# Function to start frontend
start_frontend() {
    echo -e "${BLUE}⚛️  Starting React Frontend...${NC}"
    echo -e "${YELLOW}   URL: http://localhost:3000${NC}"
    echo ""

    cd admin-frontend

    if command -v npm &> /dev/null; then
        echo -e "${YELLOW}📦 Using npm...${NC}"
        npm run dev
    elif command -v yarn &> /dev/null; then
        echo -e "${YELLOW}📦 Using yarn...${NC}"
        yarn dev
    else
        echo -e "${RED}❌ Neither npm nor yarn found${NC}"
        exit 1
    fi
}

# Check command line arguments
if [ "$1" = "backend" ]; then
    start_backend
elif [ "$1" = "frontend" ]; then
    start_frontend
else
    echo -e "${YELLOW}Usage: $0 {backend|frontend}${NC}"
    echo ""
    echo -e "${BLUE}📖 Available options:${NC}"
    echo -e "${GREEN}   $0 backend  ${NC}- Start FastAPI backend only"
    echo -e "${GREEN}   $0 frontend ${NC}- Start React frontend only"
    echo ""
    echo -e "${YELLOW}💡 To run both servers:${NC}"
    echo -e "${GREEN}   1. Open terminal 1: $0 backend${NC}"
    echo -e "${GREEN}   2. Open terminal 2: $0 frontend${NC}"
    echo ""
    echo -e "${BLUE}🌟 Quick Start:${NC}"
    echo -e "${YELLOW}   1. Backend: ${NC}http://localhost:8000"
    echo -e "${YELLOW}   2. Frontend: ${NC}http://localhost:3000"
    echo -e "${YELLOW}   3. API Docs: ${NC}http://localhost:8000/docs"
    echo -e "${YELLOW}   4. Admin Panel: ${NC}http://localhost:8000/admin"
    echo ""
    echo -e "${GREEN}🎉 Ready to start developing!${NC}"
fi
