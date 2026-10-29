#!/bin/bash
# SIGPI Deployment Script - Production Environment
# Usage: ./scripts/deploy-production.sh

set -e

echo "🚀 Deploying SIGPI to PRODUCTION environment..."
echo ""
echo "⚠️  WARNING: You are deploying to PRODUCTION!"
echo ""

# Safety confirmation
read -p "Are you sure you want to deploy to production? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Deployment cancelled"
    exit 0
fi

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo "❌ Error: .env.production not found!"
    echo "📋 Copy .env.example to .env.production and configure it"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running!"
    echo "📋 Please start Docker and try again"
    exit 1
fi

# Verify production configuration
echo "🔍 Verifying production configuration..."
if grep -q "CHANGE_THIS" .env.production; then
    echo "❌ Error: .env.production contains placeholder values!"
    echo "📋 Please update all CHANGE_THIS values with actual production credentials"
    exit 1
fi

# Check DJANGO_DEBUG is false
if grep -q "DJANGO_DEBUG=true" .env.production; then
    echo "❌ Error: DJANGO_DEBUG must be false in production!"
    exit 1
fi

# Create backup before deployment
echo "💾 Creating backup..."
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
if docker compose --env-file .env.production exec -T db pg_dump -U sigpi sigpi > "$BACKUP_DIR/db_backup.sql" 2>/dev/null; then
    echo "✅ Database backup created: $BACKUP_DIR/db_backup.sql"
else
    echo "⚠️  Database backup skipped (database may not be running)"
fi

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker compose --env-file .env.production down

# Build and start services
echo "🏗️  Building and starting services..."
docker compose --env-file .env.production up -d --build

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 20

# Run database migrations
echo "🔄 Running database migrations..."
docker compose --env-file .env.production exec -T backend python manage.py migrate --noinput

# Collect static files
echo "📦 Collecting static files..."
docker compose --env-file .env.production exec -T backend python manage.py collectstatic --noinput

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
echo "✅ Production deployment complete!"
echo ""
echo "📊 Service URLs:"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo "   Superset: http://localhost:8088"
echo ""
echo "💾 Backup location: $BACKUP_DIR"
echo "📋 View logs: docker compose --env-file .env.production logs -f"
echo "🛑 Stop services: docker compose --env-file .env.production down"
