#!/bin/bash

# MagFlow ERP - Verificare Completă
echo "🔍 Verificare completă MagFlow ERP..."
echo "========================================"

# Verificare port
echo "📡 Verificare port 8080..."
if lsof -i :8080 > /dev/null 2>&1; then
    echo "✅ Serverul rulează pe portul 8080"
else
    echo "❌ Serverul nu rulează pe portul 8080"
    echo "💡 Rulează: make start"
    exit 1
fi

# Verificare health endpoint
echo ""
echo "💚 Verificare health endpoint..."
if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo "✅ Health endpoint funcțional"
else
    echo "❌ Health endpoint nu răspunde"
fi

# Verificare API docs
echo ""
echo "📖 Verificare documentație API..."
if curl -s http://localhost:8080/docs > /dev/null 2>&1; then
    echo "✅ Documentația API este accesibilă"
else
    echo "❌ Documentația API nu este accesibilă"
fi

# Verificare API endpoint
echo ""
echo "🔗 Verificare endpoint API..."
if curl -s http://localhost:8080/api/v1/auth/simple-test > /dev/null 2>&1; then
    echo "✅ Endpoint-urile API funcționează"
else
    echo "❌ Endpoint-urile API nu funcționează"
fi

echo ""
echo "🎉 Verificare completă terminată!"
echo "📖 Accesează: http://localhost:8080/docs"
echo "💚 Health: http://localhost:8080/health"
