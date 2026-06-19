"""
Backend tests for SIGPI OIDC authentication — STRICT TDD.

Tests define the expected behavior of the OIDC authentication backend
per spec FR-001, FR-003 (email-uniqueness & account linking).

Spec reference: openspec/changes/auth/spec.md
Design reference: openspec/changes/auth/design.md
"""
import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ImproperlyConfigured

from apps.accounts.models import Role, User
from apps.institutions.models import Institution, ResearchCenter

# The backend module does not exist yet — these imports WILL fail.
# That is the point of RED: the test references code that must be built.
from apps.accounts.backends import (
    AccountLinkingError,
    SIGPIOIDCBackend,
)

# ──────────────────────────────────────────────────────────
# Test fixtures / helpers
# ──────────────────────────────────────────────────────────


def _make_claims(**overrides) -> dict:
    """Build a realistic Keycloak id_token claims dict."""
    return {
        "sub": str(uuid.uuid4()),
        "email": "researcher@example.com",
        "email_verified": True,
        "preferred_username": "jdoe",
        "sigpi_institution_id": str(uuid.uuid4()),
        "sigpi_center_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
        "sigpi_role": "researcher",
        "realm_access": {"roles": ["sigpi_researcher"]},
        **overrides,
    }


def _get_role(name: str) -> Role:
    """Get a seeded role by name."""
    return Role.objects.get(name=name)


# ──────────────────────────────────────────────────────────
# Backend Initialization
# ──────────────────────────────────────────────────────────


class TestBackendInit:
    """Backend construction and configuration."""

    def test_backend_can_be_instantiated(self):
        """The OIDC backend can be constructed without arguments."""
        backend = SIGPIOIDCBackend()
        assert backend is not None

    def test_backend_is_an_auth_backend(self):
        """The backend follows Django's authentication backend protocol."""
        backend = SIGPIOIDCBackend()
        assert hasattr(backend, "authenticate")
        assert hasattr(backend, "get_user")

    def test_backend_get_user_returns_user(self, db):
        """get_user() fetches a User by primary key."""
        user = User.objects.create_user(
            email="getuser@example.com",
            auth_source="keycloak",
        )
        backend = SIGPIOIDCBackend()
        result = backend.get_user(user.pk)
        assert result is not None
        assert result.pk == user.pk
        assert result.email == "getuser@example.com"


# ──────────────────────────────────────────────────────────
# create_user — first-time OIDC login (FR-001)
# ──────────────────────────────────────────────────────────


class TestCreateUser:
    """First-time OIDC login: creating a User from Keycloak claims."""

    def test_create_user_from_valid_claims(self, db):
        """A new User is created from valid OIDC claims."""
        institution = Institution.objects.create(
            name="Universidad Nacional",
            code="UNAL",
        )
        claims = _make_claims(sigpi_institution_id=str(institution.pk))
        backend = SIGPIOIDCBackend()

        user = backend.create_user(claims)

        assert user is not None
        assert isinstance(user, User)
        assert user.email == claims["email"]
        assert user.auth_source == User.AuthSource.KEYCLOAK
        assert str(user.keycloak_uuid) == claims["sub"]
        assert user.is_active is True
        assert user.is_superuser is False

    def test_create_user_sets_auth_source_keycloak(self, db):
        """Users created via OIDC have auth_source='keycloak'."""
        institution = Institution.objects.create(name="UdeA", code="UDEA")
        claims = _make_claims(sigpi_institution_id=str(institution.pk))
        backend = SIGPIOIDCBackend()

        user = backend.create_user(claims)

        assert user.auth_source == "keycloak"

    def test_create_user_never_creates_superuser(self, db):
        """Superuser MUST NEVER be created from Keycloak claims."""
        institution = Institution.objects.create(name="UPB", code="UPB")
        # Even if claims somehow claim superadmin role...
        claims = _make_claims(
            sigpi_institution_id=str(institution.pk),
            sigpi_role="superadmin",
            realm_access={"roles": ["sigpi_superadmin"]},
        )
        backend = SIGPIOIDCBackend()

        user = backend.create_user(claims)

        assert user.is_superuser is False
        assert user.auth_source == "keycloak"

    def test_create_user_creates_institution_membership(self, db):
        """A first-time OIDC login creates an InstitutionMembership."""
        institution = Institution.objects.create(
            name="Universidad Nacional",
            code="UNAL",
        )
        role = _get_role("Investigador")
        claims = _make_claims(
            sigpi_institution_id=str(institution.pk),
            sigpi_role="researcher",
        )
        backend = SIGPIOIDCBackend()

        user = backend.create_user(claims)

        # User should have a membership for the claimed institution
        membership = user.memberships.first()
        assert membership is not None
        assert membership.institution == institution
        assert membership.role == role

    def test_create_user_associates_centers(self, db):
        """The membership includes ResearchCenters from claims."""
        institution = Institution.objects.create(
            name="Universidad Nacional",
            code="UNAL",
        )
        center_a = ResearchCenter.objects.create(
            name="Centro A", code="CA", institution=institution,
        )
        center_b = ResearchCenter.objects.create(
            name="Centro B", code="CB", institution=institution,
        )
        claims = _make_claims(
            sigpi_institution_id=str(institution.pk),
            sigpi_center_ids=[str(center_a.pk), str(center_b.pk)],
        )
        backend = SIGPIOIDCBackend()

        user = backend.create_user(claims)
        membership = user.memberships.first()

        assert membership.centers.count() == 2
        assert center_a in membership.centers.all()
        assert center_b in membership.centers.all()

    def test_create_user_syncs_django_groups(self, db):
        """create_user() maps Keycloak realm roles to Django Groups."""
        institution = Institution.objects.create(name="UNAL", code="UNAL")
        claims = _make_claims(
            sigpi_institution_id=str(institution.pk),
            realm_access={"roles": ["sigpi_researcher"]},
        )
        backend = SIGPIOIDCBackend()

        user = backend.create_user(claims)

        # User should be in a Django Group matching the role
        group_names = list(user.groups.values_list("name", flat=True))
        assert "sigpi_researcher" in group_names


# ──────────────────────────────────────────────────────────
# update_user — returning OIDC login (FR-001)
# ──────────────────────────────────────────────────────────


class TestUpdateUser:
    """Returning OIDC login: updating claims on existing User."""

    @pytest.fixture
    def existing_user(self):
        kc_uuid = uuid.uuid4()
        institution = Institution.objects.create(name="UNAL", code="UNAL")
        role = _get_role("Investigador")
        user = User.objects.create_user(
            email="returning@example.com",
            auth_source="keycloak",
            keycloak_uuid=kc_uuid,
        )
        from apps.accounts.models import InstitutionMembership
        InstitutionMembership.objects.create(
            user=user, institution=institution, role=role,
        )
        return user, kc_uuid, institution

    def test_update_user_found_by_keycloak_uuid(self, db, existing_user):
        """Returning user is found via keycloak_uuid and claims are updated."""
        user, kc_uuid, institution = existing_user
        claims = _make_claims(
            sub=str(kc_uuid),
            email="returning@example.com",
            sigpi_institution_id=str(institution.pk),
            sigpi_role="admin",
        )
        backend = SIGPIOIDCBackend()

        returned_user = backend.update_user(user, claims)

        assert returned_user.pk == user.pk
        assert returned_user.email == "returning@example.com"

    def test_update_user_updates_role_on_claim_change(self, db, existing_user):
        """If the KC role changes, the membership role is updated."""
        user, kc_uuid, institution = existing_user
        claims = _make_claims(
            sub=str(kc_uuid),
            email="returning@example.com",
            sigpi_institution_id=str(institution.pk),
            sigpi_role="admin",
        )
        backend = SIGPIOIDCBackend()

        returned_user = backend.update_user(user, claims)

        membership = returned_user.memberships.get(institution=institution)
        assert membership.role.name == "Admin Institucional"

    def test_update_user_updates_groups(self, db, existing_user):
        """If realm_access.roles change, Django Groups are updated."""
        user, kc_uuid, institution = existing_user
        claims = _make_claims(
            sub=str(kc_uuid),
            email="returning@example.com",
            sigpi_institution_id=str(institution.pk),
            realm_access={"roles": ["sigpi_auditor"]},
        )
        backend = SIGPIOIDCBackend()

        returned_user = backend.update_user(user, claims)

        group_names = list(returned_user.groups.values_list("name", flat=True))
        assert "sigpi_auditor" in group_names


# ──────────────────────────────────────────────────────────
# Account Linking — verified email (FR-003)
# ──────────────────────────────────────────────────────────


class TestAccountLinkingVerified:
    """Auto-link accounts when Keycloak email is verified (FR-003)."""

    @pytest.fixture
    def local_user(self):
        return User.objects.create_user(
            email="linktest@example.com",
            auth_source="local",
            keycloak_uuid=None,
        )

    @pytest.fixture
    def institution(self):
        return Institution.objects.create(name="UPB", code="UPB")

    def test_auto_link_verified_email_sets_keycloak_uuid(
        self, db, local_user, institution
    ):
        """When KC email is verified and matches a local user, accounts link."""
        claims = _make_claims(
            email="linktest@example.com",
            email_verified=True,
            sigpi_institution_id=str(institution.pk),
        )
        backend = SIGPIOIDCBackend()

        user = backend.create_user(claims)

        # Same user object — keycloak_uuid is now set
        assert user.pk == local_user.pk
        assert user.keycloak_uuid is not None
        assert str(user.keycloak_uuid) == claims["sub"]

    def test_auto_link_changes_auth_source_to_keycloak(
        self, db, local_user, institution
    ):
        """Linked accounts get auth_source updated to 'keycloak'."""
        claims = _make_claims(
            email="linktest@example.com",
            email_verified=True,
            sigpi_institution_id=str(institution.pk),
        )
        backend = SIGPIOIDCBackend()

        user = backend.create_user(claims)

        assert user.auth_source == "keycloak"

    def test_auto_link_creates_membership(self, db, local_user, institution):
        """Linked accounts get an InstitutionMembership from claims."""
        claims = _make_claims(
            email="linktest@example.com",
            email_verified=True,
            sigpi_institution_id=str(institution.pk),
            sigpi_role="researcher",
        )
        backend = SIGPIOIDCBackend()

        user = backend.create_user(claims)

        assert user.memberships.filter(institution=institution).exists()


# ──────────────────────────────────────────────────────────
# Account Linking — unverified email (FR-003)
# ──────────────────────────────────────────────────────────


class TestAccountLinkingUnverified:
    """Manual confirmation required for unverified email (FR-003)."""

    @pytest.fixture
    def local_user(self):
        return User.objects.create_user(
            email="unverified@example.com",
            auth_source="local",
            keycloak_uuid=None,
        )

    def test_unverified_email_raises_account_linking_error(
        self, db, local_user
    ):
        """If KC email is unverified, linking raises AccountLinkingError."""
        institution = Institution.objects.create(name="UPB", code="UPB")
        claims = _make_claims(
            email="unverified@example.com",
            email_verified=False,  # ← unverified
            sigpi_institution_id=str(institution.pk),
        )
        backend = SIGPIOIDCBackend()

        with pytest.raises(AccountLinkingError) as exc_info:
            backend.create_user(claims)

        assert "manual" in str(exc_info.value).lower() or "confirm" in str(exc_info.value).lower()

    def test_unverified_email_does_not_modify_local_user(
        self, db, local_user
    ):
        """Unverified email linking does not change the local user."""
        institution = Institution.objects.create(name="UPB", code="UPB")
        claims = _make_claims(
            email="unverified@example.com",
            email_verified=False,
            sigpi_institution_id=str(institution.pk),
        )
        backend = SIGPIOIDCBackend()

        original_uuid = local_user.keycloak_uuid
        try:
            backend.create_user(claims)
        except AccountLinkingError:
            pass

        local_user.refresh_from_db()
        assert local_user.keycloak_uuid == original_uuid  # unchanged (None)
        assert local_user.auth_source == "local"


# ──────────────────────────────────────────────────────────
# Error handling — missing claims
# ──────────────────────────────────────────────────────────


class TestMissingClaims:
    """Graceful handling of incomplete Keycloak token claims."""

    def test_missing_sub_claim_raises_error(self, db):
        """A token without 'sub' claim should be rejected."""
        claims = _make_claims()
        del claims["sub"]
        backend = SIGPIOIDCBackend()

        with pytest.raises(ValueError):
            backend.create_user(claims)

    def test_missing_email_claim_raises_error(self, db):
        """A token without 'email' claim should be rejected."""
        claims = _make_claims()
        del claims["email"]
        backend = SIGPIOIDCBackend()

        with pytest.raises(ValueError):
            backend.create_user(claims)

    def test_missing_institution_id_is_ok_no_membership(self, db):
        """If sigpi_institution_id is missing, user is created without membership."""
        claims = _make_claims()
        del claims["sigpi_institution_id"]
        backend = SIGPIOIDCBackend()

        user = backend.create_user(claims)

        assert user is not None
        assert user.email == claims["email"]
        # No membership created
        assert user.memberships.count() == 0
