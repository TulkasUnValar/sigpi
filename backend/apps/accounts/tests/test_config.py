"""
Configuration tests for SIGPI PR 3 — STRICT TDD.

Tests verify:
- TenantMiddleware is registered in MIDDLEWARE
- TenantRLSMiddleware is registered in MIDDLEWARE
- CORS is configured for Next.js frontend origin
- Session/CSRF cookie settings are correct

Spec references: FR-004, Security Requirements
Design reference: openspec/changes/auth/design.md — Cookie Configuration
"""

from django.conf import settings


class TestMiddlewareRegistration:
    """Tenant middleware is registered in the MIDDLEWARE list."""

    def test_tenant_middleware_is_registered(self):
        """TenantMiddleware is in the MIDDLEWARE list."""
        assert "config.middleware.tenant.TenantMiddleware" in settings.MIDDLEWARE

    def test_tenant_rls_middleware_is_registered(self):
        """TenantRLSMiddleware is in the MIDDLEWARE list."""
        assert "config.middleware.tenant.TenantRLSMiddleware" in settings.MIDDLEWARE

    def test_tenant_middleware_after_auth_middleware(self):
        """TenantMiddleware must run AFTER AuthenticationMiddleware."""
        middleware_list = settings.MIDDLEWARE
        auth_idx = middleware_list.index("django.contrib.auth.middleware.AuthenticationMiddleware")
        tenant_idx = middleware_list.index("config.middleware.tenant.TenantMiddleware")
        assert tenant_idx > auth_idx, "TenantMiddleware must run after AuthenticationMiddleware"

    def test_rls_middleware_after_tenant_middleware(self):
        """TenantRLSMiddleware must run AFTER TenantMiddleware."""
        middleware_list = settings.MIDDLEWARE
        tenant_idx = middleware_list.index("config.middleware.tenant.TenantMiddleware")
        rls_idx = middleware_list.index("config.middleware.tenant.TenantRLSMiddleware")
        assert rls_idx > tenant_idx, "TenantRLSMiddleware must run after TenantMiddleware"


class TestSessionConfig:
    """Session and CSRF cookie security settings."""

    def test_session_cookie_httponly(self):
        """Session cookie is HttpOnly."""
        assert settings.SESSION_COOKIE_HTTPONLY is True

    def test_session_cookie_samesite_lax(self):
        """Session cookie uses SameSite=Lax."""
        assert settings.SESSION_COOKIE_SAMESITE == "Lax"

    def test_csrf_cookie_httponly(self):
        """CSRF cookie is HttpOnly."""
        assert settings.CSRF_COOKIE_HTTPONLY is True

    def test_csrf_cookie_samesite_lax(self):
        """CSRF cookie uses SameSite=Lax."""
        assert settings.CSRF_COOKIE_SAMESITE == "Lax"


class TestCORSConfig:
    """CORS is configured for the Next.js frontend."""

    def test_cors_is_installed(self):
        """django-cors-headers is in INSTALLED_APPS."""
        assert "corsheaders" in settings.INSTALLED_APPS

    def test_cors_middleware_is_registered(self):
        """CorsMiddleware is in the MIDDLEWARE list (before CommonMiddleware)."""
        assert "corsheaders.middleware.CorsMiddleware" in settings.MIDDLEWARE

    def test_cors_middleware_before_common(self):
        """CorsMiddleware must be before CommonMiddleware."""
        middleware_list = settings.MIDDLEWARE
        cors_idx = middleware_list.index("corsheaders.middleware.CorsMiddleware")
        common_idx = middleware_list.index("django.middleware.common.CommonMiddleware")
        assert cors_idx < common_idx, "CorsMiddleware must be before CommonMiddleware"

    def test_cors_allowed_origins(self):
        """Next.js frontend origin is in CORS allowed origins."""
        allowed = settings.CORS_ALLOWED_ORIGINS
        assert any("localhost:3000" in origin for origin in allowed), (
            "Next.js dev origin (localhost:3000) must be allowed"
        )

    def test_cors_allow_credentials(self):
        """CORS allows credentials (cookies)."""
        assert settings.CORS_ALLOW_CREDENTIALS is True
