"""
SIGPI Celery Tasks — Keycloak Role Sync.

Implements FR-008: The system MUST reconcile Keycloak roles with
Django Groups via Celery beat (every 5 minutes).

Design reference: openspec/changes/auth/design.md — Role Sync Flow
"""

import logging

from celery import shared_task
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from apps.accounts.audit import AuditEventEmitter, AuditEventType

logger = logging.getLogger(__name__)
User = get_user_model()

# Batch size for Keycloak API pagination
KC_PAGE_SIZE = 100


# ──────────────────────────────────────────────────────────
# Keycloak API Client (stub — to be wired to real KC later)
# ──────────────────────────────────────────────────────────


def _fetch_keycloak_users(page: int = 0, page_size: int = KC_PAGE_SIZE) -> list[dict]:
    """Fetch a page of users from the Keycloak Admin API.

    This is a STUB that returns an empty list. In production, this will:
    1. Get a service account token from Keycloak
    2. Call GET /admin/realms/{realm}/users?first={page*page_size}&max={page_size}
    3. Return a list of user dicts with 'id', 'email', and 'realmRoles'

    Returns:
        List of dicts: [{"id": "uuid", "email": "...", "realmRoles": [...]}, ...]
    """
    # STUB: returns empty list. Wire to real Keycloak Admin API in PR or later.
    return []


# ──────────────────────────────────────────────────────────
# Group Sync Helper
# ──────────────────────────────────────────────────────────


def _sync_user_groups(user: User, kc_roles: list[str]) -> dict:
    """Sync a single user's Django Groups to match Keycloak roles.

    Idempotent: running twice produces the same result.
    Only diffs groups — adds new ones, removes stale ones.

    Args:
        user: The Django User to sync.
        kc_roles: List of Keycloak role names (e.g., ["sigpi_researcher"]).

    Returns:
        Dict with: added (list), removed (list), changed (bool).
    """
    desired_names = set(kc_roles)

    # Ensure all desired groups exist in the DB
    for name in desired_names:
        Group.objects.get_or_create(name=name)

    current_names = set(user.groups.values_list("name", flat=True))

    added = list(desired_names - current_names)
    removed = list(current_names - desired_names)
    changed = len(added) > 0 or len(removed) > 0

    for name in removed:
        user.groups.remove(Group.objects.get(name=name))

    for name in added:
        user.groups.add(Group.objects.get(name=name))

    if changed:
        logger.info(
            "Synced groups for user %s: added=%s, removed=%s",
            user.email,
            added,
            removed,
        )

    return {"added": added, "removed": removed, "changed": changed}


# ──────────────────────────────────────────────────────────
# Celery Task
# ──────────────────────────────────────────────────────────


@shared_task(name="sync_keycloak_roles")
def sync_keycloak_roles() -> dict:
    """Sync Keycloak roles to Django Groups for all Keycloak users.

    Runs every 5 minutes via Celery beat.
    Paginates the Keycloak Admin API to fetch all users.
    For each user, diffs and updates Django Group membership.

    Returns:
        Dict with: synced (int), errors (int).
        On failure: {"error": str, "synced": 0}
    """
    try:
        synced_count = 0
        error_count = 0
        page = 0

        while True:
            kc_users = _fetch_keycloak_users(page=page, page_size=KC_PAGE_SIZE)

            if not kc_users:
                break  # No more users to process

            for kc_user in kc_users:
                kc_uuid = kc_user.get("id")
                kc_roles = kc_user.get("realmRoles", [])

                if not kc_uuid:
                    continue

                try:
                    user = User.objects.get(keycloak_uuid=kc_uuid)
                    result = _sync_user_groups(user, kc_roles)
                    synced_count += 1

                    if result["changed"]:
                        AuditEventEmitter().emit(
                            event_type=AuditEventType.ROLE_CHANGE,
                            user=user,
                            details={
                                "added": result["added"],
                                "removed": result["removed"],
                            },
                        )
                except User.DoesNotExist:
                    # User not yet synced to Django — skip
                    logger.debug(
                        "Keycloak user %s not found in Django — skipping sync",
                        kc_uuid,
                    )
                except Exception as exc:
                    logger.error("Error syncing user %s: %s", kc_uuid, exc)
                    error_count += 1

            page += 1

        return {"synced": synced_count, "errors": error_count}

    except Exception as exc:
        logger.exception("sync_keycloak_roles failed")
        return {"error": str(exc), "synced": 0}
