"""
Model tests for accounts app — STRICT TDD.

Tests define the expected behavior of User, Role, and InstitutionMembership
models per the auth spec and design documents.

Spec reference: openspec/changes/auth/spec.md
Design reference: openspec/changes/auth/design.md

Note: The seed_roles migration runs before all tests, populating
7 fixed roles. Tests that need roles should query existing ones
or use Role.objects.get_or_create().
"""
import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.accounts.models import InstitutionMembership, Role, User
from apps.institutions.models import Institution, ResearchCenter


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _get_role(name: str) -> Role:
    """Get a seeded role by name. Roles are created by seed_roles migration."""
    return Role.objects.get(name=name)


def _get_or_create_role(name: str, level: int,
                        keycloak_role_name: str = "") -> Role:
    """Get existing role or create if not seeded (for edge-case tests)."""
    role, _ = Role.objects.get_or_create(
        name=name,
        defaults={"level": level, "keycloak_role_name": keycloak_role_name},
    )
    return role


# ──────────────────────────────────────────────
# User Model Tests
# ──────────────────────────────────────────────


class TestUserCreation:
    """User model creation and basic field behavior."""

    def test_create_user_with_email(self, db):
        """A User can be created with an email and auth_source."""
        user = User.objects.create_user(
            email="researcher@example.com",
            auth_source="keycloak",
        )
        assert user.id is not None
        assert isinstance(user.id, uuid.UUID)
        assert user.email == "researcher@example.com"
        assert user.auth_source == "keycloak"
        assert user.is_active is True
        assert user.is_superuser is False

    def test_create_user_with_keycloak_uuid(self, db):
        """A Keycloak-authenticated user stores their KC UUID."""
        kc_uuid = uuid.uuid4()
        user = User.objects.create_user(
            email="oidc@example.com",
            auth_source="keycloak",
            keycloak_uuid=kc_uuid,
        )
        assert user.keycloak_uuid == kc_uuid

    def test_local_user_keycloak_uuid_null(self, db):
        """A locally-authenticated user has no keycloak_uuid."""
        user = User.objects.create_user(
            email="local@example.com",
            auth_source="local",
        )
        assert user.keycloak_uuid is None

    def test_email_is_required(self, db):
        """Creating a user without email raises ValidationError."""
        with pytest.raises(ValidationError):
            user = User(email=None, auth_source="local")
            user.full_clean()

    def test_auth_source_choices(self, db):
        """auth_source must be 'keycloak' or 'local'."""
        user = User(email="test@example.com", auth_source="invalid")
        with pytest.raises(ValidationError):
            user.full_clean()

    def test_user_string_representation(self, db):
        """User __str__ returns the email."""
        user = User.objects.create_user(
            email="strtest@example.com",
            auth_source="local",
        )
        assert str(user) == "strtest@example.com"


class TestUserUniqueness:
    """Email and keycloak_uuid uniqueness constraints."""

    def test_email_unique_constraint(self, db):
        """Two users cannot share the same email."""
        User.objects.create_user(email="dup@example.com", auth_source="local")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    email="dup@example.com",
                    auth_source="keycloak",
                )

    def test_keycloak_uuid_unique_constraint(self, db):
        """Two users cannot share the same keycloak_uuid."""
        shared_uuid = uuid.uuid4()
        User.objects.create_user(
            email="first@example.com",
            auth_source="keycloak",
            keycloak_uuid=shared_uuid,
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    email="second@example.com",
                    auth_source="keycloak",
                    keycloak_uuid=shared_uuid,
                )

    def test_keycloak_uuid_null_not_unique(self, db):
        """Multiple local users (keycloak_uuid=None) can coexist."""
        User.objects.create_user(email="local1@example.com", auth_source="local")
        User.objects.create_user(email="local2@example.com", auth_source="local")
        assert User.objects.filter(keycloak_uuid__isnull=True).count() == 2


class TestSuperuser:
    """Superuser creation and attributes."""

    def test_create_superuser(self, db):
        """A superuser is created with is_superuser=True and is_staff=True."""
        su = User.objects.create_superuser(
            email="admin@sigpi.local",
            password="supersecret",
        )
        assert su.is_superuser is True
        assert su.is_staff is True

    def test_superuser_auth_source_local(self, db):
        """Superadmin MUST be local-only per design decision."""
        su = User.objects.create_superuser(
            email="superadmin@sigpi.local",
            password="adminpass",
        )
        assert su.auth_source == "local"


# ──────────────────────────────────────────────
# Role Model Tests
# ──────────────────────────────────────────────


class TestRoleCreation:
    """Role model creation and field behavior."""

    def test_create_role_with_unique_name(self, db):
        """A Role can be created with a non-conflicting name."""
        role = _get_or_create_role(
            name="Test Role X",
            level=99,
            keycloak_role_name="sigpi_test_x",
        )
        assert role.id is not None
        assert isinstance(role.id, uuid.UUID)
        assert role.name == "Test Role X"
        assert role.keycloak_role_name == "sigpi_test_x"
        assert role.level == 99

    def test_seeded_role_exists(self, db):
        """Seeded roles from 0002_seed_roles migration are present."""
        investigador = _get_role("Investigador")
        assert investigador.level == 4
        assert investigador.keycloak_role_name == "sigpi_researcher"

    def test_role_name_unique(self, db):
        """Role names must be unique — duplicate raises IntegrityError."""
        # Use a fresh name to avoid conflicting with seeded roles
        _get_or_create_role(name="UniqueTestRole", level=50)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Role.objects.create(name="UniqueTestRole", level=60)

    def test_role_string_representation(self, db):
        """Role __str__ returns the name."""
        auditor = _get_role("Auditor")
        assert str(auditor) == "Auditor"


class TestRoleHierarchy:
    """Role hierarchy levels (1 = highest, 7 = lowest)."""

    def test_seeded_roles_have_correct_levels(self, db):
        """All 7 seeded roles match their designated hierarchy levels."""
        expected = [
            ("Superadmin", 1),
            ("Admin Institucional", 2),
            ("Director de Centro", 3),
            ("Investigador", 4),
            ("Evaluador", 5),
            ("Asistente", 6),
            ("Auditor", 7),
        ]
        for name, level in expected:
            role = _get_role(name)
            assert role.level == level, f"{name} should be level {level}"
        assert Role.objects.count() >= 7


# ──────────────────────────────────────────────
# Seed Migration Tests
# ──────────────────────────────────────────────


class TestRoleSeedMigration:
    """Verify the seed_roles data migration produces correct state."""

    def test_seed_roles_count(self, db):
        """After migration, at least 7 roles exist."""
        assert Role.objects.count() >= 7

    def test_seed_roles_superadmin(self, db):
        """Superadmin role has hierarchy level 1."""
        superadmin = _get_role("Superadmin")
        assert superadmin.level == 1
        assert superadmin.keycloak_role_name == "sigpi_superadmin"

    def test_seed_roles_auditor(self, db):
        """Auditor role has hierarchy level 7."""
        auditor = _get_role("Auditor")
        assert auditor.level == 7
        assert auditor.keycloak_role_name == "sigpi_auditor"

    def test_seed_roles_admin_institucional(self, db):
        """Admin Institucional role has hierarchy level 2."""
        admin = _get_role("Admin Institucional")
        assert admin.level == 2
        assert admin.keycloak_role_name == "sigpi_admin"


# ──────────────────────────────────────────────
# InstitutionMembership Model Tests
# ──────────────────────────────────────────────


class TestMembershipCreation:
    """InstitutionMembership join table behavior."""

    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            email="member@example.com",
            auth_source="keycloak",
        )

    @pytest.fixture
    def institution(self):
        return Institution.objects.create(
            name="Universidad Nacional",
            code="UNAL",
        )

    @pytest.fixture
    def role(self):
        """Use seeded 'Investigador' role (level 4)."""
        return _get_role("Investigador")

    def test_create_membership(self, db, user, institution, role):
        """A membership links a user to an institution with a role."""
        membership = InstitutionMembership.objects.create(
            user=user,
            institution=institution,
            role=role,
        )
        assert membership.id is not None
        assert isinstance(membership.id, uuid.UUID)
        assert membership.user == user
        assert membership.institution == institution
        assert membership.role == role
        assert membership.is_primary is False
        assert membership.is_active is True
        assert membership.joined_at is not None

    def test_membership_related_name(self, db, user, institution, role):
        """User.memberships retrieves all InstitutionMembership records."""
        InstitutionMembership.objects.create(
            user=user, institution=institution, role=role,
        )
        assert user.memberships.count() == 1
        assert user.memberships.first().institution == institution

    def test_centers_m2m(self, db, user, institution, role):
        """Membership can associate with multiple ResearchCenters."""
        center_a = ResearchCenter.objects.create(
            name="Centro A", institution=institution, code="CA",
        )
        center_b = ResearchCenter.objects.create(
            name="Centro B", institution=institution, code="CB",
        )
        membership = InstitutionMembership.objects.create(
            user=user, institution=institution, role=role,
        )
        membership.centers.add(center_a, center_b)
        assert membership.centers.count() == 2
        assert center_a in membership.centers.all()

    def test_membership_string_representation(self, db, user, institution, role):
        """InstitutionMembership __str__ includes user email and institution."""
        membership = InstitutionMembership.objects.create(
            user=user, institution=institution, role=role,
        )
        expected = f"member@example.com — Universidad Nacional"
        assert str(membership) == expected


class TestMembershipConstraints:
    """Unique and integrity constraints on InstitutionMembership."""

    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            email="constraint@example.com",
            auth_source="local",
        )

    @pytest.fixture
    def institution(self):
        return Institution.objects.create(
            name="Instituto X", code="IX",
        )

    @pytest.fixture
    def role(self):
        return _get_role("Admin Institucional")

    def test_unique_user_institution(self, db, user, institution, role):
        """A user can only have one membership per institution."""
        InstitutionMembership.objects.create(
            user=user, institution=institution, role=role,
        )
        with pytest.raises(ValidationError):
            InstitutionMembership.objects.create(
                user=user, institution=institution, role=role,
            )

    def test_different_institution_allowed(self, db, user, institution, role):
        """A user can have memberships in multiple institutions."""
        inst_b = Institution.objects.create(
            name="Universidad B", code="UB",
        )
        InstitutionMembership.objects.create(
            user=user, institution=institution, role=role,
        )
        InstitutionMembership.objects.create(
            user=user, institution=inst_b, role=role,
        )
        assert user.memberships.count() == 2

    def test_is_primary_default_false(self, db, user, institution, role):
        """New memberships default to is_primary=False."""
        membership = InstitutionMembership.objects.create(
            user=user, institution=institution, role=role,
        )
        assert membership.is_primary is False

    def test_is_active_default_true(self, db, user, institution, role):
        """New memberships default to is_active=True."""
        membership = InstitutionMembership.objects.create(
            user=user, institution=institution, role=role,
        )
        assert membership.is_active is True
