"""
Recipient resolution for the notifications module.

Queries active InstitutionMembership rows and returns distinct users.
Role levels are authoritative (design decision): Director de Centro = 3,
Admin Institucional = 2.

Resolvers never raise: a missing recipient yields [] so receivers can
log a warning and keep the sender transaction intact.
"""

from apps.accounts.models import InstitutionMembership

DIRECTOR_LEVEL = 3
# Actors empowered to authorize over-execution (budget spec RN-020 /
# CanAuthorizeExecution level <= 3): Admin Institucional (2) and
# Director de Centro (3).
ADMIN_LEVELS = (2, 3)


def resolve_director(institution, center):
    """Active center directors of ``center`` within ``institution`` (RN-1).

    A center director is an active membership in the project's
    institution whose role level is Director (3) and whose centers M2M
    includes the project's center.
    """
    if center is None:
        return []
    memberships = InstitutionMembership.objects.filter(
        institution=institution,
        is_active=True,
        role__level=DIRECTOR_LEVEL,
        centers=center,
        user__is_active=True,
    ).select_related("user")
    return list(dict.fromkeys(m.user for m in memberships))


def resolve_project_pi(project):
    """Principal investigator's User for a project (RN-3).

    Project.principal_investigator is a Researcher; the notification
    recipient is the linked User. Returns [] when the researcher has no
    linked system user.
    """
    researcher = project.principal_investigator
    if researcher is None or researcher.user_id is None:
        return []
    return [researcher.user]


def resolve_researcher(progress_report):
    """The report author (created_by) — RN-2."""
    user = progress_report.created_by
    return [user] if user is not None else []


def resolve_admin(institution):
    """Institutional administrators for an institution (RN-4).

    Includes Admin Institucional (level 2) and Director de Centro
    (level 3) — the actors who can authorize over-execution.
    """
    memberships = InstitutionMembership.objects.filter(
        institution=institution,
        is_active=True,
        role__level__in=ADMIN_LEVELS,
        user__is_active=True,
    ).select_related("user")
    return list(dict.fromkeys(m.user for m in memberships))
