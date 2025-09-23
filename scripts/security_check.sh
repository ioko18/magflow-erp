#!/bin/bash
# Security validation script for MagFlow ERP
# This script checks for common security issues in environment configuration

set -e

echo "🔒 MagFlow ERP Security Validation"
echo "=================================="

# Check if .env file exists and contains real secrets
if [ -f ".env" ]; then
    echo "✅ .env file exists"

    # Check for placeholder passwords (these should be changed)
    if grep -q "change_me" .env; then
        echo "❌ WARNING: Found 'change_me' placeholder in .env file"
        echo "   Please change default passwords before deploying"
    fi

    # Check for weak passwords (very short or common words)
    if grep -q "password.*password" .env || grep -q "pass.*123" .env; then
        echo "❌ WARNING: Found potentially weak passwords in .env file"
    fi

    # Check if secrets are different from development defaults
    if grep -q "your-super-secure-secret-key-change-this-in-production" .env; then
        echo "❌ CRITICAL: Default SECRET_KEY found in .env file"
        echo "   This must be changed for production deployment"
        exit 1
    fi
else
    echo "❌ .env file not found"
fi

# Check if .env is properly gitignored
if [ -f ".gitignore" ]; then
    if grep -q "^\.env$" .gitignore; then
        echo "✅ .env is properly gitignored"
    else
        echo "❌ WARNING: .env is not in .gitignore"
    fi
else
    echo "❌ .gitignore file not found"
fi

# Check for debug mode in production-like environments
if [ -f ".env.production" ]; then
    if grep -q "APP_DEBUG.*true" .env.production 2>/dev/null; then
        echo "❌ WARNING: Debug mode enabled in production environment"
    else
        echo "✅ Debug mode properly disabled for production"
    fi
fi

# Check Docker security
if [ -f "docker-compose.yml" ]; then
    echo "✅ Docker Compose configuration found"

    # Check for exposed ports (this is normal for web apps)
    if grep -q "ports:" docker-compose.yml; then
        echo "ℹ️  Docker ports exposed (expected for web application)"
    fi
fi

# Check for SSL certificates
if [ -d "certs" ] && [ -d "ssl" ]; then
    echo "✅ SSL certificate directories found"
else
    echo "❌ WARNING: SSL certificate directories not found"
fi

echo ""
echo "Security validation completed!"
echo "Review any warnings above and address them before production deployment."
