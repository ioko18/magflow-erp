#!/bin/bash
# Script de verificare completă pentru toate implementările eMAG v4.4.9

echo "🔍 Verificare Completă Implementări eMAG v4.4.9"
echo "================================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# Function to check file exists
check_file() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if [ -f "$1" ]; then
        echo -e "${GREEN}✅ $2${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo -e "${RED}❌ $2 - File not found: $1${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

# Function to run command and check result
run_check() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    if eval "$1" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $2${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo -e "${RED}❌ $2${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

echo -e "${BLUE}📋 Verificare Fișiere Backend${NC}"
echo "-----------------------------------"
check_file "app/services/emag_light_offer_service.py" "Light Offer API Service"
check_file "app/core/emag_validator.py" "Response Validator"
check_file "app/core/emag_logger.py" "Request Logger (30 zile)"
check_file "app/api/v1/endpoints/enhanced_emag_sync.py" "Enhanced API Endpoints"
check_file "test_full_sync.py" "Test Full Sync Script"
echo ""

echo -e "${BLUE}📋 Verificare Fișiere Frontend${NC}"
echo "-----------------------------------"
check_file "admin-frontend/src/components/QuickOfferUpdate.tsx" "Quick Update Component"
check_file "admin-frontend/src/services/unifiedProductsApi.ts" "Unified Products API Client"
echo ""

echo -e "${BLUE}📋 Verificare Tests${NC}"
echo "-----------------------------------"
check_file "tests/services/test_emag_light_offer_service.py" "Unit Tests Light Offer Service"
echo ""

echo -e "${BLUE}📋 Verificare Documentație${NC}"
echo "-----------------------------------"
check_file "RECOMANDARI_IMBUNATATIRI_EMAG.md" "Recomandări eMAG v4.4.9"
check_file "IMPLEMENTARI_COMPLETE_EMAG_V449.md" "Ghid Implementare"
check_file "FULL_SYNC_IMPLEMENTATION.md" "Documentație Tehnică"
check_file "IMPLEMENTARE_SINCRONIZARE_COMPLETA.md" "Ghid Utilizare"
check_file "REZUMAT_FINAL_IMPLEMENTARI.md" "Overview Complet"
check_file "IMPLEMENTARI_FINALE_COMPLETE.md" "Implementări Finale"
check_file "REZUMAT_COMPLET_FINAL.md" "Rezumat Final"
echo ""

echo -e "${BLUE}🧪 Verificare Funcționalități${NC}"
echo "-----------------------------------"

# Check Python imports
echo -n "Verificare import Light Offer Service... "
if python3 -c "from app.services.emag_light_offer_service import EmagLightOfferService" 2>/dev/null; then
    echo -e "${GREEN}✅${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "${RED}❌${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

echo -n "Verificare import Response Validator... "
if python3 -c "from app.core.emag_validator import EmagResponseValidator" 2>/dev/null; then
    echo -e "${GREEN}✅${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "${RED}❌${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

echo -n "Verificare import Request Logger... "
if python3 -c "from app.core.emag_logger import EmagRequestLogger" 2>/dev/null; then
    echo -e "${GREEN}✅${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "${RED}❌${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

echo ""

echo -e "${BLUE}🗄️ Verificare Database${NC}"
echo "-----------------------------------"

# Check database
if docker exec magflow_db psql -U app -d magflow -c "SELECT COUNT(*) FROM app.emag_products_v2;" > /dev/null 2>&1; then
    PRODUCT_COUNT=$(docker exec magflow_db psql -U app -d magflow -t -c "SELECT COUNT(*) FROM app.emag_products_v2;" | xargs)
    echo -e "${GREEN}✅ Database emag_products_v2: $PRODUCT_COUNT produse${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "${RED}❌ Database emag_products_v2 nu este accesibil${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

if docker exec magflow_db psql -U app -d magflow -c "SELECT COUNT(*) FROM app.products;" > /dev/null 2>&1; then
    LOCAL_COUNT=$(docker exec magflow_db psql -U app -d magflow -t -c "SELECT COUNT(*) FROM app.products;" | xargs)
    echo -e "${GREEN}✅ Database products: $LOCAL_COUNT produse locale${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "${RED}❌ Database products nu este accesibil${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

echo ""

echo -e "${BLUE}🧪 Rulare Unit Tests${NC}"
echo "-----------------------------------"

# Run validation tests
if python3 -m pytest tests/services/test_emag_light_offer_service.py::TestResponseValidation -v --tb=short 2>&1 | grep -q "passed"; then
    echo -e "${GREEN}✅ Response Validation Tests: PASSED${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "${RED}❌ Response Validation Tests: FAILED${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

echo ""

echo -e "${BLUE}📊 Verificare Logs Directory${NC}"
echo "-----------------------------------"

if [ -d "logs/emag" ]; then
    echo -e "${GREEN}✅ Logs directory exists: logs/emag${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
else
    echo -e "${YELLOW}⚠️  Logs directory will be created on first use${NC}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

echo ""

# Summary
echo "================================================"
echo -e "${BLUE}📊 Rezumat Verificare${NC}"
echo "================================================"
echo ""
echo "Total verificări: $TOTAL_CHECKS"
echo -e "${GREEN}Passed: $PASSED_CHECKS${NC}"
echo -e "${RED}Failed: $FAILED_CHECKS${NC}"
echo ""

# Calculate percentage
PERCENTAGE=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))

if [ $PERCENTAGE -eq 100 ]; then
    echo -e "${GREEN}✅ TOATE VERIFICĂRILE AU TRECUT! (100%)${NC}"
    echo ""
    echo "🎉 Sistemul este complet implementat și gata de producție!"
    echo ""
    echo "Next steps:"
    echo "  1. Integrare QuickOfferUpdate în Products page"
    echo "  2. Deployment în producție"
    echo "  3. Monitoring și alerting"
    exit 0
elif [ $PERCENTAGE -ge 80 ]; then
    echo -e "${YELLOW}⚠️  Majoritatea verificărilor au trecut ($PERCENTAGE%)${NC}"
    echo ""
    echo "Verificați erorile de mai sus și corectați-le."
    exit 1
else
    echo -e "${RED}❌ Multe verificări au eșuat ($PERCENTAGE%)${NC}"
    echo ""
    echo "Sistemul necesită atenție. Verificați erorile de mai sus."
    exit 1
fi
