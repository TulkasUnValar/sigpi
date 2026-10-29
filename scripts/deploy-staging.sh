#!/bin/bash
# SIGPI Deployment Script - Staging Environment
# Usage: ./scripts/deploy-staging.sh

set -e

echo "🚀 Deploying SIGPI to STAGING environment..."

# Check if .env.staging exists
if [ ! -f ".env.staging" ]; then
    echo "❌ Error: .env.staging not found!"
    echo "📋 Copy .env.example to .env.staging and configure it"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running!"
    echo "📋 Please start Docker and try again"
    exit 1
fi

# Verify staging configuration
echo "🔍 Verifying staging configuration..."
if grep -q "CHANGE_THIS" .env.staging; then
    echo "❌ Error: .env.staging contains placeholder values!"
    echo "📋 Please update all CHANGE_THIS values with actual staging credentials"
    exit 1
fi

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker compose --env-file .env.staging down

# Build and start services
echo "🏗️  Building and starting services..."
docker compose --env-file .env.staging up -d --build

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 15

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
echo "✅ Staging deployment complete!"
echo ""
echo "📊 Service URLs:"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo "   Superset: http://localhost:8088"
echo ""
echo "📋 View logs: docker compose --env-file .env.staging logs -f"
echo "🛑 Stop services: docker compose --env-file .env.staging down"
