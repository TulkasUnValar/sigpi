# Delta for projects-ui

## MODIFIED Requirements

### Requirement: Create wizard

`/projects/new` MUST be a multi-step wizard (basic info → center/group/line → team → documents) with per-step validation and a review step before submit. The team/principal-investigator researcher selects MUST consume the paginated researcher endpoint: `useResearchers()` MUST fetch `Page<ResearcherList>` from `/api/researchers/` and map `results` to `{id, full_name}` options so the wizard renders correctly against the real API (previously the wizard mapped a bare `ResearcherOption[]`, which crashed against the paginated envelope).

#### Scenario: Wizard submit

- GIVEN all steps valid
- WHEN submit is pressed
- THEN POST `/projects/` succeeds and redirects to detail

#### Scenario: Paginated researcher options

- GIVEN the wizard's team/PI step and a paginated researchers API
- WHEN `useResearchers()` resolves
- THEN the PI and team selects render options from `results`, not the raw envelope

#### Scenario: Researchers page 2

- GIVEN more than 25 researchers and no next page fetched
- WHEN the wizard researcher query resolves
- THEN only the first page's options are offered (no crash from the envelope)

## PR Boundaries

- PR3 — wizard pagination fix + polish: `features/projects/queries.ts` (`useResearchers()` → `Page<ResearcherList>`), `app/projects/new/page.tsx` mapping, matching MSW researchers handler.
