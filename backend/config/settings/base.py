"""
Django base settings for SIGPI.

Multi-institution research project management system.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-change-me-in-production-7a3b2c1d4e5f6a7b8c9d0e1f",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS: list[str] = os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,backend"
).split(",")

# Application definition
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "mozilla_django_oidc",
    "allauth",
    "allauth.account",
    "corsheaders",
    "django_filters",
    "storages",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.audit",
    "apps.institutions",
    "apps.notifications",
    "apps.researchers",
    "apps.projects",
    "apps.progress",
    "apps.products",
    "apps.calls",
    "apps.budgets",
    "apps.reports",
    "apps.project_workflow",
    "apps.documents",
    "apps.search",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "config.middleware.tenant.TenantMiddleware",
    "config.middleware.tenant.TenantRLSMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
# Use in-memory SQLite during testing (PYTEST_RUNNING=true)
# unless POSTGRES_HOST is explicitly provided (CI / Docker).
if os.environ.get("PYTEST_RUNNING") == "true" and not os.environ.get("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "sigpi"),
            "USER": os.environ.get("POSTGRES_USER", "sigpi"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "sigpi"),
            "HOST": os.environ.get("POSTGRES_HOST", "db"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }

# Custom User model
AUTH_USER_MODEL = "accounts.User"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}

# ──────────────────────────────────────────────────────────
# Authentication Backends
# ──────────────────────────────────────────────────────────
# Order matters: OIDC is tried first for OIDC callback URLs;
# allauth/ModelBackend handle local login endpoint.
AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.SIGPIOIDCBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# ──────────────────────────────────────────────────────────
# OIDC (Keycloak) Configuration
# ──────────────────────────────────────────────────────────
OIDC_RP_CLIENT_ID = os.environ.get("OIDC_RP_CLIENT_ID", "sigpi-app")
OIDC_RP_CLIENT_SECRET = os.environ.get("OIDC_RP_CLIENT_SECRET", "sigpi-client-secret-change-me")
OIDC_RP_SIGN_ALGO = "RS256"
OIDC_RP_SCOPES = "openid email profile sigpi-custom-claims"
OIDC_OP_AUTHORIZATION_ENDPOINT = os.environ.get(
    "OIDC_OP_AUTHORIZATION_ENDPOINT",
    "http://keycloak:8080/realms/sigpi/protocol/openid-connect/auth",
)
OIDC_OP_TOKEN_ENDPOINT = os.environ.get(
    "OIDC_OP_TOKEN_ENDPOINT",
    "http://keycloak:8080/realms/sigpi/protocol/openid-connect/token",
)
OIDC_OP_USER_ENDPOINT = os.environ.get(
    "OIDC_OP_USER_ENDPOINT",
    "http://keycloak:8080/realms/sigpi/protocol/openid-connect/userinfo",
)
OIDC_OP_JWKS_ENDPOINT = os.environ.get(
    "OIDC_OP_JWKS_ENDPOINT",
    "http://keycloak:8080/realms/sigpi/protocol/openid-connect/certs",
)
OIDC_OP_LOGOUT_ENDPOINT = os.environ.get(
    "OIDC_OP_LOGOUT_ENDPOINT",
    "http://keycloak:8080/realms/sigpi/protocol/openid-connect/logout",
)
OIDC_OP_ISSUER = os.environ.get(
    "OIDC_OP_ISSUER",
    "http://keycloak:8080/realms/sigpi",
)
OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS = int(
    os.environ.get("OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS", "3600")
)
OIDC_STORE_ID_TOKEN = True
OIDC_CREATE_USER = True
OIDC_REDIRECT_REQUIRE_HTTPS = os.environ.get("OIDC_REDIRECT_REQUIRE_HTTPS", "False").lower() in (
    "true",
    "1",
    "yes",
)
LOGIN_REDIRECT_URL = os.environ.get("LOGIN_REDIRECT_URL", "/")
LOGOUT_REDIRECT_URL = os.environ.get("LOGOUT_REDIRECT_URL", "/auth/login/")

# ──────────────────────────────────────────────────────────
# django-allauth Configuration
# ──────────────────────────────────────────────────────────
# Local auth fallback only — social login is out of MVP scope.
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
# Deprecated allauth settings replaced above (v0.63+)
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_VERIFICATION = "none"  # Local verification handled by SIGPI
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_LOGIN_ON_PASSWORD_RESET = False

# ──────────────────────────────────────────────────────────
# Test-only overrides (fast password hashing, DB sessions)
# ──────────────────────────────────────────────────────────
if os.environ.get("PYTEST_RUNNING") == "true":
    SESSION_ENGINE = "django.contrib.sessions.backends.db"
    # Fast password hasher — PBKDF2 (720k iterations) makes create_user()
    # take ~1s each. MD5 takes ~1ms. Only for tests; never in production.
    PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.MD5PasswordHasher",
    ]
else:
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False").lower() in (
    "true",
    "1",
    "yes",
)
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 28800  # 8 hours
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "False").lower() in ("true", "1", "yes")
CSRF_COOKIE_SAMESITE = "Lax"

# ──────────────────────────────────────────────────────────
# Cache (Redis)
# ──────────────────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ.get("REDIS_URL", "redis://redis:6379/1"),
    }
}

# ──────────────────────────────────────────────────────────
# Celery (Redis broker & backend)
# ──────────────────────────────────────────────────────────
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/2")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/3")

# ──────────────────────────────────────────────────────────
# Meilisearch (search module)
# ──────────────────────────────────────────────────────────
# Full-text search engine (RNF-014). Dev defaults match the
# docker-compose service; production values come from env.
MEILISEARCH_URL = os.environ.get("MEILISEARCH_URL", "http://localhost:7700")
MEILISEARCH_API_KEY = os.environ.get("MEILISEARCH_API_KEY", "masterKey")

# ──────────────────────────────────────────────────────────
# MinIO / S3 Storage (documents module)
# ──────────────────────────────────────────────────────────
# Files never transit Django: the backend issues presigned URLs against
# MinIO (S3 API) and clients upload/download directly. The bucket is
# private; object-level ACLs stay unset (bucket policy enforces privacy).
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET_NAME = os.environ.get("MINIO_BUCKET_NAME", "sigpi-documents")
MINIO_REGION = os.environ.get("MINIO_REGION", "us-east-1")
# Presigned URL expiry (seconds): PUT <= 30 min, GET <= 15 min per spec.
MINIO_PRESIGN_PUT_EXPIRY = int(os.environ.get("MINIO_PRESIGN_PUT_EXPIRY", "1800"))
MINIO_PRESIGN_GET_EXPIRY = int(os.environ.get("MINIO_PRESIGN_GET_EXPIRY", "900"))

STORAGES = {
    "default": {
        "BACKEND": "apps.documents.storage.MinIOStorage",
        "OPTIONS": {
            "access_key": MINIO_ACCESS_KEY,
            "secret_key": MINIO_SECRET_KEY,
            "bucket_name": MINIO_BUCKET_NAME,
            "endpoint_url": MINIO_ENDPOINT,
            "region_name": MINIO_REGION,
            "querystring_auth": True,
            "querystring_expire": MINIO_PRESIGN_GET_EXPIRY,
        },
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# ──────────────────────────────────────────────────────────
# Site ID (required by django-allauth)
# ──────────────────────────────────────────────────────────
SITE_ID = 1

# ──────────────────────────────────────────────────────────
# CORS Configuration (Next.js frontend)
# ──────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://frontend:3000",
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False
