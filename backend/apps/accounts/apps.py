import logging

from django.apps import AppConfig
from django.contrib.auth.signals import user_logged_in

logger = logging.getLogger(__name__)


def _handle_user_logged_in(sender, request, user, **kwargs):
    """Emit LOGIN audit events for OIDC (Keycloak) logins.

    Local logins are handled explicitly in local_login_view.
    This signal handler catches OIDC logins from mozilla-django-oidc's
    callback view (which calls auth.login after token validation).
    """
    # Only emit for Keycloak users — local logins are handled by views.py
    if user.auth_source != "keycloak":
        return

    from apps.accounts.audit import AuditEventEmitter, AuditEventType

    emitter = AuditEventEmitter()
    emitter.emit(
        event_type=AuditEventType.LOGIN,
        user=user,
        ip_address=emitter.extract_ip(request),
        institution_id=request.session.get("institution_id"),
        details={"auth_source": "keycloak"},
    )


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Accounts"

    def ready(self):
        """Connect signal handlers when the app is ready."""
        user_logged_in.connect(
            _handle_user_logged_in,
            dispatch_uid="accounts_oidc_login_audit",
        )
