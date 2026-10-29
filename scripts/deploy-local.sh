#!/bin/bash
# SIGPI Deployment Script - Local Environment
# Usage: ./scripts/deploy-local.sh

set -e

echo "🚀 Deploying SIGPI to LOCAL environment..."

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo "❌ Error: .env.local not found!"
    echo "📋 Copy .env.example to .env.local and configure it"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running!"
    echo "📋 Please start Docker and try again"
    exit 1
fi

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker compose --env-file .env.local down

# Build and start services
echo "🏗️  Building and starting services..."
docker compose --env-file .env.local up -d --build

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🔍 Checking service health..."
if curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
    echo "✅ Backend is healthy"
else
    echo "⚠️  Backend health check failed (may still be starting)"
fi

if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend is healthy"
else
    echo "⚠️  Frontend health check failed (may still be starting)"
fi

echo ""
echo "✅ Local deployment complete!"
echo ""
echo "📊 Service URLs:"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo "   Superset: http://localhost:8088"
echo "   Keycloak: http://localhost:8080"
echo "   MinIO:    http://localhost:9001"
echo ""
echo "📋 View logs: docker compose --env-file .env.local logs -f"
echo "🛑 Stop services: docker compose --env-file .env.local down"
