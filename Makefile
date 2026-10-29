.PHONY: test test-fast lint format check docker-up docker-down

# Run all tests (from repo root, using backend config)
test:
	pytest -c backend/pyproject.toml

# Run only fast tests (no slow markers)
test-fast:
	pytest -c backend/pyproject.toml -m "not slow"

# Run tests for a specific app
test-app:
	pytest -c backend/pyproject.toml backend/apps/$(app)/tests/

# Run tests with coverage
test-cov:
	pytest -c backend/pyproject.toml --cov=backend/apps --cov-report=term-missing

# Run ruff linter on backend
check:
	cd backend && ruff check apps/

# Auto-fix ruff issues
fix:
	cd backend && ruff check --fix apps/

# Format all code
format:
	cd backend && ruff format apps/

# Full audit: format + lint + tests
audit: format check test

# Start development stack
docker-up:
	docker compose --env-file .env.local up -d

# Stop development stack
docker-down:
	docker compose --env-file .env.local down

# ============================================================================
# Deployment Commands by Environment
# ============================================================================

# Deploy to local environment
deploy-local:
	@echo "🚀 Deploying to LOCAL environment..."
	docker compose --env-file .env.local up -d --build
	@echo "✅ Local deployment complete"
	@echo "📊 Backend: http://localhost:8000"
	@echo "📊 Frontend: http://localhost:3000"
	@echo "📊 Superset: http://localhost:8088"

# Deploy to staging environment
deploy-staging:
	@echo "🚀 Deploying to STAGING environment..."
	docker compose --env-file .env.staging up -d --build
	@echo "✅ Staging deployment complete"

# Deploy to production environment
deploy-production:
	@echo "🚀 Deploying to PRODUCTION environment..."
	@echo "⚠️  WARNING: You are deploying to PRODUCTION!"
	@read -p "Are you sure? (yes/no): " confirm && [ "$$confirm" = "yes" ] || exit 1
	docker compose --env-file .env.production up -d --build
	@echo "✅ Production deployment complete"

# Stop all services for specific environment
deploy-down:
	@echo "🛑 Stopping services..."
	docker compose --env-file .env.local down || \
	docker compose --env-file .env.staging down || \
	docker compose --env-file .env.production down
	@echo "✅ Services stopped"

# View logs for specific environment
deploy-logs:
	@echo "📋 Showing logs..."
	docker compose --env-file .env.local logs -f || \
	docker compose --env-file .env.staging logs -f || \
	docker compose --env-file .env.production logs -f
