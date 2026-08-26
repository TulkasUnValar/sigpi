"""Search API view — validates index/filters and injects tenant scope.

Implements ``GET /api/search/`` (spec RF-090/RF-091, tenant isolation):

- validates the requested index and client filters (400 on unknown
  index, malformed JSON, or unsupported filter keys)
- injects the server-owned tenant scope for non-superusers
  (``institution_id == request.institution_id``); superusers may omit it
- passes the query through to Meilisearch and returns the ranked response
  preserving ``hits``, ``query``, ``processingTimeMs`` and pagination
  metadata (SDK ``SearchResults.model_dump(by_alias=True)``).
"""

from rest_framework.response import Response
from rest_framework.views import APIView

from apps.search.client import get_client
from apps.search.filters import build_filter_expression, parse_filters


def _parse_int(raw: str | None, default: int) -> int:
    """Parse an optional integer query parameter, falling back to ``default``."""
    try:
        return int(raw) if raw is not None else default
    except ValueError:
        return default


class SearchAPIView(APIView):
    """GET /api/search/?q=<text>&index=<name>&filters=<JSON>"""

    def get(self, request):
        index_name = request.query_params.get("index")
        if index_name is None:
            return Response(
                {"detail": "Missing 'index' query parameter."}, status=400
            )
        try:
            client_filters = parse_filters(
                index_name, request.query_params.get("filters")
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)

        query = request.query_params.get("q", "")
        offset = _parse_int(request.query_params.get("offset"), 0)
        limit = _parse_int(request.query_params.get("limit"), 20)

        # Non-superusers always search within their active institution.
        # The scope is server-owned: client filters cannot override it.
        institution_id = None if request.user.is_superuser else request.institution_id
        filter_expression = build_filter_expression(
            client_filters, institution_id=institution_id
        )

        index = get_client().index(index_name)
        results = index.search(
            query, filter=filter_expression, offset=offset, limit=limit
        )
        return Response(results.model_dump(by_alias=True))
