# Search Specification (SIGPI §6.11)

## Purpose

Provide full-text search across institutional entities using Meilisearch. The search module indexes 5 entity types (projects, researchers, products, calls, advances) with tenant isolation, filtering, and faceted navigation. Search is read-only and institution-scoped (RF-080..RF-089).

## Architecture

The search module consists of:

- **Backend**: Django REST API wrapping Meilisearch client, with tenant isolation enforced at the filter level
- **Frontend**: React components (SearchBar, SearchResults, SearchFilters) using TanStack Query
- **Indexers**: Document projections mapping Django models to Meilisearch flat documents
- **Signals**: Automatic index updates on entity create/update/delete

## Data Model

The search module does not own data models. It indexes existing domain models into Meilisearch:

| Index | Source Model | Document Shape |
|---|---|---|
| `projects` | `Project` | `{id, institution_id, center_id, line_id, title, abstract, objectives, methodology, expected_results, keywords, status, year}` |
| `researchers` | `Researcher` | `{id, institution_id, center_id, line_id, first_name, last_name, primary_email, document_number, bio, academic_formation, is_active}` |
| `products` | `ResearchProduct` | `{id, institution_id, title, description, type, publication_year, year}` |
| `calls` | `Call` | `{id, institution_id, title, description, external_entity, call_type, type, status, submission_start, year}` |
| `advances` | `ProgressReport` | `{id, institution_id, center_id, project_title, description, activities, difficulties, next_steps, status, period_start, year}` |

## Index Configuration

Each index declares searchable and filterable attributes:

```python
INDEX_CONFIG = {
    "projects": {
        "searchable": ["title", "abstract", "objectives", "methodology", "expected_results", "keywords"],
        "filterable": ["institution_id", "center_id", "line_id", "status", "year"],
    },
    "researchers": {
        "searchable": ["first_name", "last_name", "primary_email", "document_number", "bio", "academic_formation"],
        "filterable": ["institution_id", "center_id", "line_id", "is_active"],
    },
    "products": {
        "searchable": ["title", "description", "type", "publication_year"],
        "filterable": ["institution_id", "type", "year"],
    },
    "calls": {
        "searchable": ["title", "description", "external_entity", "call_type", "status", "submission_start"],
        "filterable": ["institution_id", "type", "status", "year"],
    },
    "advances": {
        "searchable": ["description", "activities", "difficulties", "next_steps", "project_title", "status", "period_start"],
        "filterable": ["institution_id", "status", "year", "center_id"],
    },
}
```

## Functional Requirements

### Requirement: RF-S01 — Search Endpoint (RF-080)

The system MUST expose a search endpoint that queries Meilisearch with tenant isolation.

#### Scenario: Authenticated user searches
- GIVEN an authenticated user with `request.institution_id`
- WHEN GET `/api/search/?q=research&index=projects`
- THEN the system queries Meilisearch with `filter=institution_id = '<user_institution_id>'` and returns ranked hits

#### Scenario: Search across all indexes
- GIVEN an authenticated user
- WHEN GET `/api/search/?q=budget` (no `index` parameter)
- THEN the system queries all 5 indexes and returns aggregated results

#### Scenario: Missing institution context
- GIVEN a request without `request.institution_id`
- WHEN GET `/api/search/?q=test`
- THEN the system returns 400 with `{"detail": "Institution context required."}`

### Requirement: RF-S02 — Tenant Isolation (RF-081)

The system MUST enforce tenant isolation by injecting `institution_id` filter. Client-supplied `institution_id` filters MUST be silently dropped.

#### Scenario: Non-superuser cannot override tenant scope
- GIVEN a non-superuser with `institution_id = A`
- WHEN GET `/api/search/?q=test&filters={"institution_id": "B"}`
- THEN the system ignores the client `institution_id` and enforces `institution_id = A`

#### Scenario: Superuser can search without tenant filter
- GIVEN a superuser
- WHEN GET `/api/search/?q=test`
- THEN the system queries without `institution_id` filter (cross-institution search)

#### Scenario: Tenant filter in response
- GIVEN any search request
- WHEN the response is returned
- THEN all hits contain `institution_id` matching the request's tenant scope

### Requirement: RF-S03 — Filter Validation (RF-082)

The system MUST validate client-supplied filters against the index's filterable attributes.

#### Scenario: Valid filter
- GIVEN the `projects` index with filterable `status`
- WHEN GET `/api/search/?q=test&index=projects&filters={"status": "activo"}`
- THEN the system applies the filter and returns matching hits

#### Scenario: Unknown filter key
- GIVEN the `projects` index without filterable `unknown_field`
- WHEN GET `/api/search/?q=test&index=projects&filters={"unknown_field": "value"}`
- THEN the system returns 400 with `{"detail": "Unknown filter key: unknown_field"}`

#### Scenario: Malformed JSON filters
- GIVEN a search request
- WHEN GET `/api/search/?q=test&filters=not-json`
- THEN the system returns 400 with `{"detail": "filters must be valid JSON"}`

### Requirement: RF-S04 — Filter Aliases (RF-083)

The system MUST map user-facing filter keys to document attributes:

| User-facing Key | Document Attribute |
|---|---|
| `institution` | `institution_id` |
| `center` | `center_id` |
| `line` | `line_id` |

#### Scenario: Alias mapping
- GIVEN a search request with `filters={"institution": "uuid"}`
- WHEN the filter is processed
- THEN the system translates it to `institution_id = 'uuid'` before querying Meilisearch

### Requirement: RF-S05 — Pagination (RF-084)

The system MUST support offset-based pagination with configurable limit.

#### Scenario: Default pagination
- GIVEN a search request without pagination parameters
- WHEN the query is executed
- THEN the system returns `offset=0, limit=20` by default

#### Scenario: Custom pagination
- GIVEN a search request with `offset=40&limit=10`
- WHEN the query is executed
- THEN the system returns hits 41-50 with pagination metadata

#### Scenario: Pagination metadata
- GIVEN a search returning 150 total hits
- WHEN the response is serialized
- THEN the response includes `hits`, `query`, `processingTimeMs`, `estimatedTotalHits`, `offset`, `limit`

### Requirement: RF-S06 — Index Management (RF-085)

The system MUST provide a management command to create indexes and backfill data.

#### Scenario: Create indexes
- GIVEN an empty Meilisearch instance
- WHEN `python manage.py reindex_search` is executed
- THEN the system creates 5 indexes with correct searchable/filterable settings

#### Scenario: Backfill data
- GIVEN existing Django models
- WHEN `python manage.py reindex_search --backfill` is executed
- THEN the system indexes all entities into their respective indexes

#### Scenario: Recreate indexes
- GIVEN existing indexes with stale data
- WHEN `python manage.py reindex_search --recreate` is executed
- THEN the system deletes and recreates all indexes, then backfills

#### Scenario: Index single entity type
- GIVEN a request to reindex only projects
- WHEN `python manage.py reindex_search --index=projects` is executed
- THEN only the `projects` index is recreated and backfilled

### Requirement: RF-S07 — Automatic Indexing (RF-086)

The system MUST automatically update indexes when entities are created, updated, or deleted.

#### Scenario: Entity created
- GIVEN a new `Project` instance
- WHEN the instance is saved
- THEN the system enqueues a Celery task to index the project document

#### Scenario: Entity updated
- GIVEN an existing `Researcher` instance
- WHEN the instance's `bio` field is updated
- THEN the system enqueues a Celery task to update the researcher document in Meilisearch

#### Scenario: Entity deleted
- GIVEN an existing `ResearchProduct` instance
- WHEN the instance is deleted
- THEN the system enqueues a Celery task to remove the product document from Meilisearch

#### Scenario: Batch indexing
- GIVEN multiple entities created in a transaction
- WHEN the transaction commits
- THEN the system batches index updates into a single Celery task

## API Contract

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/api/search/` | GET | Session | Full-text search with filters |

### Query Parameters

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `q` | string | Yes | — | Search query text |
| `index` | string | No | all | Index name: `projects`, `researchers`, `products`, `calls`, `advances` |
| `filters` | JSON string | No | `{}` | Filter object with user-facing keys |
| `offset` | int | No | 0 | Pagination offset |
| `limit` | int | No | 20 | Results per page (max 1000) |

### Response Shape

```json
{
  "hits": [
    {
      "id": "uuid",
      "institution_id": "uuid",
      "title": "Project Title",
      "abstract": "...",
      "_formatted": {
        "title": "Project <em>Title</em>",
        "abstract": "..."
      }
    }
  ],
  "query": "title",
  "processingTimeMs": 12,
  "estimatedTotalHits": 150,
  "offset": 0,
  "limit": 20
}
```

## Meilisearch Integration

### Client Configuration

- Meilisearch host: `http://meilisearch:7700` (Docker) or `http://localhost:7700` (dev)
- API key: `MEILI_MASTER_KEY` environment variable
- Timeout: 5 seconds for queries, 30 seconds for indexing

### Document ID Convention

- All documents use the entity's UUID as the primary key
- `id` field is always a string (Meilisearch requires string primary keys)
- `institution_id` is always a string for tenant filter comparison

### Index Settings

Each index MUST have:
- `searchableAttributes`: as defined in `INDEX_CONFIG`
- `filterableAttributes`: as defined in `INDEX_CONFIG`
- `rankingRules`: default Meilisearch ranking (words, typo, proximity, attribute, sort, exactness)
- `highlightPreTag`: `<em>`
- `highlightPostTag`: `</em>`

## Frontend Integration

### Components

- `SearchBar`: Debounced input with index selector dropdown
- `SearchResults`: Paginated results with highlighted matches
- `SearchFilters`: Faceted filter panel (status, year, center, line)

### Query Hook

```typescript
export function useSearch({
  query,
  index = "all",
  filters = {},
  offset = 0,
  limit = 25,
}: SearchParams) {
  const institutionId = useActiveInstitutionId();
  return useQuery({
    queryKey: queryKeys.search.list(institutionId, query, index, filters),
    queryFn: () => api.get<SearchResults>(`/api/search/?${params}`),
    enabled: query.length >= 2,
  });
}
```

### Highlighting

- Meilisearch wraps matches in `<em>` tags in the `_formatted` field
- Frontend renders highlighted text with `dangerouslySetInnerHTML` (safe: Meilisearch escapes user input)

## Authorization

- All search requests require authentication
- Non-superusers are automatically scoped to their `institution_id`
- Superusers can search across all institutions
- No role-based restrictions beyond authentication

## Performance Requirements

- Search queries SHOULD complete in < 200ms for typical workloads
- Indexing operations SHOULD complete in < 5 seconds per entity
- Meilisearch index size SHOULD be < 1 GB for 100K documents
- Frontend debouncing: 300ms delay before triggering search

## Error Handling

| Error | Status | Response |
|---|---|---|
| Missing institution context | 400 | `{"detail": "Institution context required."}` |
| Unauthenticated | 401 | `{"detail": "Authentication credentials were not provided."}` |
| Unknown index | 400 | `{"detail": "Unknown index: <name>"}` |
| Unknown filter key | 400 | `{"detail": "Unknown filter key: <key>"}` |
| Malformed JSON filters | 400 | `{"detail": "filters must be valid JSON"}` |
| Meilisearch unreachable | 503 | `{"detail": "Search service unavailable"}` |

## Acceptance Criteria

- [ ] Search endpoint returns correct hits for test queries
- [ ] Tenant isolation enforced (non-superuser cannot see other institutions)
- [ ] Filter validation rejects unknown keys with 400
- [ ] Pagination works with offset/limit parameters
- [ ] `reindex_search` command creates indexes and backfills data
- [ ] Automatic indexing on entity create/update/delete
- [ ] Frontend components render with highlighting and pagination
- [ ] Coverage on `apps.search` ≥ 80%
- [ ] All RF-S01..RF-S07 scenarios pass under pytest

## Non-Functional Requirements

- Search MUST be read-only; no write operations allowed
- Meilisearch indexes MUST be rebuilt after schema changes
- Celery tasks for indexing MUST be idempotent
- Frontend MUST debounce search input to avoid excessive API calls
- Highlighted HTML MUST be sanitized before rendering
