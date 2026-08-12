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
	docker-compose up -d

# Stop development stack
docker-down:
	docker-compose down
