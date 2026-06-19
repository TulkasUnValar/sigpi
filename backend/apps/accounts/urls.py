"""Auth URL routing for SIGPI accounts app."""
from django.urls import path

from mozilla_django_oidc.views import OIDCAuthenticationCallbackView

from . import views

urlpatterns = [
    path("auth/keycloak-status/", views.keycloak_health_view, name="keycloak_health"),
    path("auth/login/", views.local_login_view, name="local_login"),
    path("auth/logout/", views.logout_view, name="logout"),
    path("auth/me/", views.auth_me_view, name="auth_me"),
    path("auth/link-account/", views.account_linking_view, name="account_linking"),
    path("auth/switch-institution/", views.switch_institution_view, name="switch_institution"),
    path("auth/callback/", OIDCAuthenticationCallbackView.as_view(), name="oidc_callback"),
]
