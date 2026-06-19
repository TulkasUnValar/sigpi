"""
Authentication & Authorization models for SIGPI.

Implements the data model defined in design.md:
- User: UUID PK, email-unique, keycloak_uuid nullable, auth_source choices
- Role: 7 fixed roles with hierarchy levels
- InstitutionMembership: join table linking User↔Institution with Role
"""
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models


# ──────────────────────────────────────────────
# User Manager
# ──────────────────────────────────────────────


class UserManager(BaseUserManager):
    """Custom manager for User model — email is the unique identifier."""

    def create_user(self, email: str, auth_source: str = "local",
                    password: str | None = None, **extra_fields) -> "User":
        if not email:
            raise ValidationError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, auth_source=auth_source, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str,
                         **extra_fields) -> "User":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("auth_source", "local")
        return self.create_user(email, password=password, **extra_fields)


# ──────────────────────────────────────────────
# User Model
# ──────────────────────────────────────────────


class User(AbstractBaseUser, PermissionsMixin):
    """Custom User model with UUID PK, email as identifier.

    Design decisions:
    - UUID PK for external safety across institutions
    - Email is the unique login identifier (no username)
    - keycloak_uuid is set on first OIDC login, null for local users
    - auth_source tracks origin (keycloak | local)
    - Superadmin MUST be local-only
    """

    class AuthSource(models.TextChoices):
        KEYCLOAK = "keycloak", "Keycloak"
        LOCAL = "local", "Local"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(
        unique=True,
        db_index=True,
        error_messages={"unique": "A user with this email already exists."},
    )
    keycloak_uuid = models.UUIDField(
        unique=True,
        null=True,
        blank=True,
        help_text="Keycloak user UUID — set on first OIDC login",
    )
    auth_source = models.CharField(
        max_length=20,
        choices=AuthSource.choices,
        default=AuthSource.LOCAL,
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(
        default=False,
        help_text="Designates whether the user can log into the Django admin.",
    )
    is_superuser = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "accounts_user"
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["email"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(
                fields=["keycloak_uuid"],
                name="idx_user_keycloak_uuid",
                condition=models.Q(keycloak_uuid__isnull=False),
            ),
        ]

    def clean(self):
        super().clean()
        if self.auth_source not in self.AuthSource.values:
            raise ValidationError(
                {"auth_source": f"Must be one of: {', '.join(self.AuthSource.values)}"}
            )

    def __str__(self) -> str:
        return self.email


# ──────────────────────────────────────────────
# Role Model
# ──────────────────────────────────────────────


class Role(models.Model):
    """Fixed role with hierarchy level.

    Hierarchy (1 = highest privilege, 7 = lowest):
    1. Superadmin
    2. Admin Institucional
    3. Director de Centro
    4. Investigador
    5. Evaluador
    6. Asistente
    7. Auditor
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    keycloak_role_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Corresponding Keycloak client role name",
    )
    level = models.IntegerField(
        help_text="Hierarchy rank: 1 (highest, Superadmin) to 7 (lowest, Auditor)",
    )

    class Meta:
        db_table = "accounts_role"
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        ordering = ["level"]

    def __str__(self) -> str:
        return self.name


# ──────────────────────────────────────────────
# InstitutionMembership Model
# ──────────────────────────────────────────────


class InstitutionMembership(models.Model):
    """Join table linking a User to an Institution with a Role.

    Design decisions:
    - Multi-institution: a user can belong to many institutions
    - One membership per user-institution pair (UniqueConstraint)
    - is_primary: at most one per user (enforced in clean/save)
    - centers M2M: which research centers the user belongs to
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    institution = models.ForeignKey(
        "institutions.Institution",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name="memberships",
    )
    centers = models.ManyToManyField(
        "institutions.ResearchCenter",
        blank=True,
        related_name="memberships",
    )
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_institutionmembership"
        verbose_name = "Institution Membership"
        verbose_name_plural = "Institution Memberships"
        ordering = ["user", "institution"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "institution"],
                name="unique_membership_per_user_institution",
            ),
        ]

    def clean(self):
        super().clean()
        if self.is_primary:
            conflicting = (
                InstitutionMembership.objects
                .filter(user=self.user, is_primary=True)
                .exclude(pk=self.pk)
            )
            if conflicting.exists():
                raise ValidationError(
                    {"is_primary": "User already has a primary membership."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.user.email} — {self.institution.name}"


# Import AuditEvent so Django discovers it for migrations.
# AuditEvent is defined in audit.py to keep concerns separated.
from apps.accounts.audit import AuditEvent  # noqa: E402, F401
