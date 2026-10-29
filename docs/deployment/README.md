# SIGPI Deployment Guide

This guide covers deploying SIGPI to different environments: local, staging, and production.

## Prerequisites

- Docker and Docker Compose installed
- At least 4GB RAM available
- Ports 8000, 3000, 8088, 8080, 9001 available

## Environment Overview

SIGPI supports three deployment environments:

| Environment | Purpose | Debug | Database | Use Case |
|-------------|---------|-------|----------|----------|
| **Local** | Development | ✅ Enabled | Local PostgreSQL | Daily development |
| **Staging** | Pre-production | ❌ Disabled | Separate staging DB | QA and testing |
| **Production** | Live system | ❌ Disabled | Production DB | End users |

## Quick Start

### Local Development

```bash
# Copy environment template
cp .env.example .env.local

# Start all services
./scripts/deploy-local.sh

# Or using Make
make deploy-local
```

Services will be available at:
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- Superset: http://localhost:8088
- Keycloak: http://localhost:8080
- MinIO Console: http://localhost:9001

### Staging Deployment

```bash
# 1. Copy and configure staging environment
cp .env.example .env.staging
nano .env.staging  # Update all CHANGE_THIS values

# 2. Deploy
./scripts/deploy-staging.sh

# Or using Make
make deploy-staging
```

**Important**: Update all placeholder values in `.env.staging` before deploying.

### Production Deployment

```bash
# 1. Copy and configure production environment
cp .env.example .env.production
nano .env.production  # Update all CHANGE_THIS values

# 2. Deploy (requires confirmation)
./scripts/deploy-production.sh

# Or using Make
make deploy-production
```

**Security Checklist**:
- ✅ All `CHANGE_THIS` values updated with strong credentials
- ✅ `DJANGO_DEBUG=false`
- ✅ Email configuration set
- ✅ Database backups configured
- ✅ SSL/TLS certificates in place (for domain access)

## Environment Variables

All environment-specific configuration is managed through `.env` files:

- `.env.example` - Template with all required variables
- `.env.local` - Local development (gitignored)
- `.env.staging` - Staging environment (commited with placeholders)
- `.env.production` - Production environment (commited with placeholders)

### Key Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Django secret key | `your-secret-key-here` |
| `POSTGRES_PASSWORD` | Database password | `secure-password` |
| `OIDC_RP_CLIENT_SECRET` | Keycloak client secret | `client-secret` |
| `MINIO_ROOT_PASSWORD` | MinIO admin password | `minio-password` |
| `MEILISEARCH_API_KEY` | Search engine API key | `search-api-key` |
| `SUPERSET_SECRET_KEY` | Superset secret key | `superset-secret` |

## Deployment Commands

### Manual Deployment

```bash
# Start specific environment
docker compose --env-file .env.local up -d
docker compose --env-file .env.staging up -d
docker compose --env-file .env.production up -d

# View logs
docker compose --env-file .env.local logs -f

# Stop services
docker compose --env-file .env.local down

# Rebuild after code changes
docker compose --env-file .env.local up -d --build
```

### Using Make

```bash
# Deploy to environment
make deploy-local
make deploy-staging
make deploy-production

# View logs
make deploy-logs

# Stop services
make deploy-down
```

### Using Scripts

```bash
# Deploy with health checks
./scripts/deploy-local.sh
./scripts/deploy-staging.sh
./scripts/deploy-production.sh
```

## Database Migrations

Migrations run automatically during production deployment. For manual execution:

```bash
# Run migrations
docker compose --env-file .env.production exec backend python manage.py migrate

# Create migrations (development only)
docker compose --env-file .env.local exec backend python manage.py makemigrations
```

## Backups

### Automatic Backups

Production deployment script automatically creates database backups in `backups/` directory.

### Manual Backups

```bash
# Backup database
docker compose --env-file .env.production exec -T db pg_dump -U sigpi sigpi > backup.sql

# Restore database
docker compose --env-file .env.production exec -T db psql -U sigpi sigpi < backup.sql
```

## Troubleshooting

### Services Not Starting

```bash
# Check logs
docker compose --env-file .env.local logs

# Check specific service
docker compose --env-file .env.local logs backend

# Restart services
docker compose --env-file .env.local restart
```

### Database Connection Issues

```bash
# Check database health
docker compose --env-file .env.local exec db pg_isready -U sigpi

# Reset database (WARNING: destroys data)
docker compose --env-file .env.local down -v
./scripts/deploy-local.sh
```

### Port Conflicts

If ports are already in use:
1. Stop conflicting services
2. Or modify port mappings in `docker-compose.yml`

## Monitoring

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health/

# Frontend
curl http://localhost:3000

# Check all services
docker compose --env-file .env.local ps
```

### Logs

```bash
# Real-time logs
docker compose --env-file .env.local logs -f

# Last 100 lines
docker compose --env-file .env.local logs --tail=100

# Specific service
docker compose --env-file .env.local logs -f backend
```

## Security Best Practices

1. **Never commit `.env.local`** - Contains real credentials
2. **Use strong passwords** - All `CHANGE_THIS` values must be replaced
3. **Enable HTTPS** - Use reverse proxy (nginx, Traefik) for staging/production
4. **Regular backups** - Schedule automated database backups
5. **Update dependencies** - Keep Docker images and dependencies updated
6. **Limit access** - Restrict access to staging/production environments

## CI/CD Integration

The deployment configuration integrates with GitHub Actions CI/CD:

- Automated testing on all PRs
- E2E tests with Playwright
- Staging deployment on merge to main
- Production deployment on tag creation

See `.github/workflows/ci.yml` for details.

## Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [Next.js Deployment](https://nextjs.org/docs/deployment)
- [Apache Superset Installation](https://superset.apache.org/docs/installation/installing-superset-using-docker-compose)

## Support

For deployment issues:
1. Check logs: `docker compose --env-file .env.local logs`
2. Verify environment variables in `.env.*` files
3. Ensure Docker has sufficient resources
4. Check port availability
5. Review this documentation
