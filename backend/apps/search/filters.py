"""Filter validation and Meilisearch filter expression building (SIGPI §6.11).

Each index declares the user-facing filter keys the API accepts (spec
Index Layout). Layout keys map onto the document attributes declared in
``INDEX_CONFIG`` (design: the API filter whitelist maps user-facing layout
keys → document attributes):

- ``institution`` → ``institution_id``
- ``center``     → ``center_id``
- ``line``       → ``line_id``
- remaining keys (``status``, ``year``, ``type``, ``is_active``) map to
  themselves.

Tenant isolation: ``institution_id`` is a reserved, server-owned attribute.
Client-supplied ``institution_id`` filters are silently dropped — the view
injects the request-scoped tenant scope (spec: "MUST NOT trust client
filters"; design: "assert outgoing filter contains only server tenant
scope").

``build_filter_expression`` renders the AND-combined Meilisearch ``filter``
list (a flat string list is AND-joined by Meilisearch), quoting string
values and leaving numbers/booleans bare.
"""

import json

from apps.search.indexers import INDEX_CONFIG

# User-facing layout keys → document filterable attributes.
LAYOUT_FILTER_ALIASES = {
    "institution": "institution_id",
    "center": "center_id",
    "line": "line_id",
}

# Server-owned document attributes never accepted from the client.
_RESERVED_ATTRIBUTES = {"institution_id"}


def _layout_key(attribute: str) -> str:
    """Reverse the layout alias mapping (attribute → user-facing key)."""
    for layout_key, attr in LAYOUT_FILTER_ALIASES.items():
        if attr == attribute:
            return layout_key
    return attribute


def filterable_keys(index_name: str) -> dict[str, str]:
    """Map the user-facing filter keys of ``index_name`` to document attributes."""
    try:
        attributes = INDEX_CONFIG[index_name]["filterable"]
    except KeyError:
        raise ValueError(f"Unknown search index: {index_name}") from None
    return {
        _layout_key(attribute): attribute
        for attribute in attributes
        if attribute not in _RESERVED_ATTRIBUTES
    }


def parse_filters(index_name: str, raw_filters: str | None) -> dict[str, object]:
    """Validate and normalize the client ``filters`` JSON for ``index_name``.

    Returns ``{document_attribute: value}``. Raises ``ValueError`` with a
    client-facing message when the index is unknown, the JSON is malformed
    or not an object, or a filter key is not declared for the index.
    Reserved attributes (``institution_id``) are silently dropped.
    """
    whitelist = filterable_keys(index_name)
    if raw_filters in (None, ""):
        return {}
    try:
        payload = json.loads(raw_filters)
    except json.JSONDecodeError:
        raise ValueError("filters must be a valid JSON object.") from None
    if not isinstance(payload, dict):
        raise ValueError("filters must be a JSON object.")
    normalized: dict[str, object] = {}
    for key, value in payload.items():
        if key == "institution_id":
            continue  # server-owned — never trust client scope
        try:
            attribute = whitelist[key]
        except KeyError:
            raise ValueError(
                f"Unsupported filter key for index '{index_name}': '{key}'"
            ) from None
        normalized[attribute] = value
    return normalized


def _render_filter_value(value: object) -> str:
    """Render a filter value using Meilisearch filter syntax."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return f"'{value}'"


def build_filter_expression(
    client_filters: dict[str, object], *, institution_id: str | None = None
) -> list[str] | None:
    """Build the Meilisearch ``filter`` list (AND-combined strings).

    The server-owned tenant scope is injected first when provided. Returns
    ``None`` when no filter part exists (e.g. superuser without filters).
    """
    parts = []
    if institution_id is not None:
        parts.append(f"institution_id = '{institution_id}'")
    parts.extend(
        f"{attribute} = {_render_filter_value(value)}"
        for attribute, value in client_filters.items()
    )
    return parts or None
