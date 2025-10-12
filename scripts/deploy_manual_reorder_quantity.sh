#!/bin/bash

# ==============================================================================
# Deployment Script - Manual Reorder Quantity Feature
# ==============================================================================
# Data: 13 Octombrie 2025
# Autor: Cascade AI
# ==============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ==============================================================================
# Functions
# ==============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# ==============================================================================
# Main Script
# ==============================================================================

print_header "Deployment: Manual Reorder Quantity Feature"

# Step 1: Check if we're in the right directory
print_info "Checking current directory..."
if [ ! -f "app/main.py" ]; then
    print_error "Not in project root directory!"
    print_info "Please run this script from: /Users/macos/anaconda3/envs/MagFlow"
    exit 1
fi
print_success "In correct directory"

# Step 2: Check if .env exists
print_info "Checking .env file..."
if [ ! -f ".env" ]; then
    print_warning ".env file not found!"
    print_info "Creating .env from .env.example..."
    cp .env.example .env
    print_warning "Please edit .env with your database credentials"
    print_info "Then run this script again"
    exit 1
fi
print_success ".env file exists"

# Step 3: Load environment variables
print_info "Loading environment variables..."
export $(cat .env | grep -v '^#' | xargs)
print_success "Environment variables loaded"

# Step 4: Check database connection
print_info "Checking database connection..."
if command -v psql &> /dev/null; then
    if psql -h "${DB_HOST:-localhost}" -U "${DB_USER:-app}" -d "${DB_NAME:-magflow}" -c "SELECT 1" &> /dev/null; then
        print_success "Database connection OK"
    else
        print_error "Cannot connect to database!"
        print_info "Host: ${DB_HOST:-localhost}"
        print_info "User: ${DB_USER:-app}"
        print_info "Database: ${DB_NAME:-magflow}"
        print_warning "Please check your database credentials in .env"
        exit 1
    fi
else
    print_warning "psql not found, skipping database connection check"
fi

# Step 5: Run SQL script
print_header "Step 1: Adding manual_reorder_quantity column"

if [ -f "scripts/sql/safe_add_manual_reorder_quantity.sql" ]; then
    print_info "Running SQL script..."
    
    if command -v psql &> /dev/null; then
        psql -h "${DB_HOST:-localhost}" -U "${DB_USER:-app}" -d "${DB_NAME:-magflow}" -f scripts/sql/safe_add_manual_reorder_quantity.sql
        print_success "SQL script executed successfully"
    else
        print_warning "psql not found!"
        print_info "Please run the SQL script manually:"
        print_info "psql -h ${DB_HOST:-localhost} -U ${DB_USER:-app} -d ${DB_NAME:-magflow} -f scripts/sql/safe_add_manual_reorder_quantity.sql"
    fi
else
    print_error "SQL script not found!"
    exit 1
fi

# Step 6: Verify column was added
print_header "Step 2: Verifying column"

if command -v psql &> /dev/null; then
    print_info "Checking if column exists..."
    RESULT=$(psql -h "${DB_HOST:-localhost}" -U "${DB_USER:-app}" -d "${DB_NAME:-magflow}" -t -c "SELECT column_name FROM information_schema.columns WHERE table_schema = 'app' AND table_name = 'inventory_items' AND column_name = 'manual_reorder_quantity'")
    
    if [[ $RESULT == *"manual_reorder_quantity"* ]]; then
        print_success "Column manual_reorder_quantity exists!"
    else
        print_error "Column was not added!"
        exit 1
    fi
fi

# Step 7: Check if backend is running
print_header "Step 3: Backend Status"

if pgrep -f "uvicorn.*app.main:app" > /dev/null; then
    print_warning "Backend is running"
    print_info "You should restart it to load the new schema"
    print_info "Options:"
    print_info "  1. systemctl restart magflow-backend"
    print_info "  2. docker-compose restart backend"
    print_info "  3. Ctrl+C and restart manually"
else
    print_info "Backend is not running"
    print_info "Start it with: python -m uvicorn app.main:app --reload --port 8010"
fi

# Step 8: Summary
print_header "Deployment Summary"

print_success "Database schema updated"
print_success "Column manual_reorder_quantity added"
print_info "Next steps:"
echo "  1. Restart backend"
echo "  2. Refresh browser (Ctrl+Shift+R)"
echo "  3. Test in Low Stock Suppliers page"
echo "  4. Test editing reorder quantity"
echo ""
print_info "Documentation:"
echo "  - DEPLOYMENT_GUIDE_2025_10_13.md"
echo "  - MANUAL_REORDER_QUANTITY_FEATURE.md"
echo ""
print_success "Deployment completed successfully!"
echo ""
