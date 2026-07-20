"""
SIGPI OIDC Authentication Backend.

Implements the authentication backend chain defined in design.md:
- Primary: SIGPIOIDCBackend (Keycloak OIDC via mozilla-django-oidc)
- Creates/updates local User from Keycloak claims
- Account linking: auto if email verified, manual if not
- Superadmin is NEVER created from Keycloak

Spec references: FR-001, FR-003
Design reference: openspec/changes/auth/design.md — OIDC Login Flow
"""

import logging
import uuid as uuid_module

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from apps.accounts.models import InstitutionMembership, Role
from apps.institutions.models import Institution, ResearchCenter

logger = logging.getLogger(__name__)
User = get_user_model()


# ──────────────────────────────────────────────────────────
# Custom Exceptions
# ──────────────────────────────────────────────────────────


class AccountLinkingError(Exception):
    """Raised when automatic account linking is not possible.

    Per spec FR-003: unverified email requires manual confirmation.
    """

    def __init__(self, message: str = "Confirm account linking manually."):
        self.message = message
        super().__init__(message)


# ──────────────────────────────────────────────────────────
# Role → Django Group mapping helpers
# ──────────────────────────────────────────────────────────

# Map Keycloak realm/client role names to SIGPI Role names
KC_ROLE_TO_ROLE_NAME: dict[str, str] = {
    # Full KC client role names
    "sigpi_superadmin": "Superadmin",
    "sigpi_admin": "Admin Institucional",
    "sigpi_center_director": "Director de Centro",
    "sigpi_researcher": "Investigador",
    "sigpi_coinvestigator": "Evaluador",
    "sigpi_committee": "Asistente",
    "sigpi_auditor": "Auditor",
    # Short-hand names (as they appear in sigpi_role claim)
    "superadmin": "Superadmin",
    "admin": "Admin Institucional",
    "center_director": "Director de Centro",
    "researcher": "Investigador",
    "coinvestigator": "Evaluador",
    "committee": "Asistente",
    "auditor": "Auditor",
}


def _sync_groups(user: User, realm_roles: list[str]) -> None:
    """Sync Django Groups from Keycloak realm_access.roles.

    Each Keycloak client role is mapped to a Django Group.
    Groups not present in the token are removed from the user.
    """
    desired_group_names = set()
    for kc_role in realm_roles:
        group_name = kc_role  # Keep KC role name as group name
        group, _ = Group.objects.get_or_create(name=group_name)
        desired_group_names.add(group_name)

    current_group_names = set(user.groups.values_list("name", flat=True))

    # Remove groups no longer in token
    for name_to_remove in current_group_names - desired_group_names:
        user.groups.remove(Group.objects.get(name=name_to_remove))

    # Add new groups
    for name_to_add in desired_group_names - current_group_names:
        user.groups.add(Group.objects.get(name=name_to_add))


def _map_kc_role_to_sigpi_role(kc_role_name: str) -> Role | None:
    """Map a Keycloak realm role name to a SIGPI Role instance."""
    if kc_role_name in KC_ROLE_TO_ROLE_NAME:
        sigpi_role_name = KC_ROLE_TO_ROLE_NAME[kc_role_name]
        try:
            return Role.objects.get(name=sigpi_role_name)
        except Role.DoesNotExist:
            logger.warning(
                "SIGPI Role '%s' not found for KC role '%s'",
                sigpi_role_name,
                kc_role_name,
            )
            return None
    return None


# ──────────────────────────────────────────────────────────
# Backend
# ──────────────────────────────────────────────────────────


class SIGPIOIDCBackend(OIDCAuthenticationBackend):
    """Custom OIDC backend for Keycloak integration.

    Extends mozilla-django-oidc to:
    - Create/update local User from Keycloak claims
    - Link accounts by verified email
    - Sync InstitutionMembership and ResearchCenters
    - Sync Django Groups from realm_access.roles
    """

    def create_user(self, claims: dict) -> User:
        """Create a new User from Keycloak OIDC claims.

        Called on first-time OIDC login.
        Implements account linking per FR-003:
        - Auto-link if email is verified and matches existing local user
        - Raise AccountLinkingError if email matches but is unverified

        Args:
            claims: The id_token claims dictionary from Keycloak.

        Returns:
            The created (or linked) User instance.

        Raises:
            ValueError: If required claims (sub, email) are missing.
            AccountLinkingError: If email matches but is unverified.
        """
        sub = claims.get("sub")
        email = claims.get("email")

        if not sub:
            raise ValueError("Token missing required claim: 'sub'")
        if not email:
            raise ValueError("Token missing required claim: 'email'")

        kc_uuid = uuid_module.UUID(sub)
        email_verified = claims.get("email_verified", False)

        # ── Account linking: check for existing user by email ──
        existing_by_email = User.objects.filter(email=email).first()
        if existing_by_email is not None:
            if email_verified:
                # Auto-link: update existing local user with KC data
                user = existing_by_email
                user.keycloak_uuid = kc_uuid
                user.auth_source = User.AuthSource.KEYCLOAK
                user.save(update_fields=["keycloak_uuid", "auth_source"])
                logger.info("Auto-linked user %s (email verified)", user.email)
            else:
                # Manual confirmation required
                raise AccountLinkingError("Email not verified. Manual account linking required.")
        else:
            # Brand-new Keycloak user
            user = User.objects.create_user(
                email=email,
                auth_source=User.AuthSource.KEYCLOAK,
                keycloak_uuid=kc_uuid,
                is_superuser=False,  # NEVER create superuser from KC
            )
            logger.info("Created new Keycloak user: %s", user.email)

        # ── Sync membership and groups ──
        self._sync_membership(user, claims)
        self._sync_realm_groups(user, claims)

        return user

    def update_user(self, user: User, claims: dict) -> User:
        """Update an existing User with fresh Keycloak claims.

        Called on each subsequent OIDC login for an existing user.

        Args:
            user: The existing User instance.
            claims: The id_token claims dictionary from Keycloak.

        Returns:
            The updated User instance.
        """
        logger.info("Updating user %s from Keycloak claims", user.email)

        # Update email if changed (rare, but possible via KC admin)
        new_email = claims.get("email")
        if new_email and new_email != user.email:
            user.email = new_email
            user.save(update_fields=["email"])

        # Sync membership and groups
        self._sync_membership(user, claims)
        self._sync_realm_groups(user, claims)

        return user

    def get_user(self, user_id):
        """Fetch User by primary key."""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    def authenticate(self, request, **kwargs):
        """Delegates to parent OIDCAuthenticationBackend.

        The parent class handles token validation. This backend's
        create_user/update_user are called by the parent after
        successful token validation.
        """
        return super().authenticate(request, **kwargs)

    # ── Internal helpers ──

    def _sync_membership(self, user: User, claims: dict) -> None:
        """Create or update InstitutionMembership from claims.

        Extracts sigpi_institution_id, sigpi_center_ids, and
        sigpi_role from the token claims.
        """
        institution_id = claims.get("sigpi_institution_id")
        if not institution_id:
            logger.debug(
                "No sigpi_institution_id in claims for user %s — skipping membership sync",
                user.email,
            )
            return

        try:
            institution = Institution.objects.get(pk=institution_id)
        except Institution.DoesNotExist:
            logger.warning(
                "Institution %s not found for user %s — skipping",
                institution_id,
                user.email,
            )
            return

        # Determine role
        kc_role_name = claims.get("sigpi_role", "researcher")
        role = _map_kc_role_to_sigpi_role(kc_role_name)
        if role is None:
            # Fallback: try to find by KC role name prefix match
            role_name = KC_ROLE_TO_ROLE_NAME.get(kc_role_name)
            if role_name:
                try:
                    role = Role.objects.get(name=role_name)
                except Role.DoesNotExist:
                    pass
            if role is None:
                logger.warning(
                    "No role mapping for KC role '%s' — defaulting to 'Investigador'",
                    kc_role_name,
                )
                role = Role.objects.get(name="Investigador")

        # Create or update membership
        membership, created = InstitutionMembership.objects.get_or_create(
            user=user,
            institution=institution,
            defaults={"role": role, "is_primary": True},
        )
        if not created:
            # Update existing membership role
            membership.role = role
            membership.save(update_fields=["role"])

        # Sync centers
        center_ids = claims.get("sigpi_center_ids", [])
        if center_ids:
            existing_center_ids = list(
                ResearchCenter.objects.filter(
                    pk__in=center_ids,
                    institution=institution,
                    is_active=True,
                ).values_list("pk", flat=True)
            )
            membership.centers.set(existing_center_ids)

    def _sync_realm_groups(self, user: User, claims: dict) -> None:
        """Sync Django Groups from realm_access.roles in claims."""
        realm_access = claims.get("realm_access", {})
        realm_roles = realm_access.get("roles", [])
        if realm_roles:
            _sync_groups(user, realm_roles)
