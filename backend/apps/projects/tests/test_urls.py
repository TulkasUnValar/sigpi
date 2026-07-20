"""
Tests for projects URL routing (Phase 3.7).

Verifies URL pattern structure — named URL patterns, path structure —
following the researchers test_urls.py pattern. URL resolution (reverse())
is deferred to Phase 4 when viewsets are fully implemented.

Strict TDD: this file is written BEFORE urls.py exists.
Expected failure: ImportError (urls.py not created yet).
"""


# ──────────────────────────────────────────────────────────
# Module structure
# ──────────────────────────────────────────────────────────


class TestURLModuleExists:
    """Verify the urls module is importable and has expected shape."""

    def test_urls_module_imports(self):
        """urls.py must be importable as a Python module."""
        from apps.projects import urls

        assert urls is not None

    def test_app_name_set(self):
        """app_name must be set for URL namespace resolution."""
        from apps.projects import urls

        assert urls.app_name == "projects"

    def test_router_registered(self):
        """SimpleRouter must be configured with Project ViewSet."""
        from apps.projects import urls

        assert hasattr(urls, "router")
        assert len(urls.router.registry) >= 1
        prefix, _viewset, basename = urls.router.registry[0]
        assert prefix == "projects"
        assert basename == "project"

    def test_urlpatterns_is_list(self):
        """urlpatterns must be a non-empty list."""
        from apps.projects import urls

        assert isinstance(urls.urlpatterns, list)
        assert len(urls.urlpatterns) > 0


# ──────────────────────────────────────────────────────────
# URL name coverage (22 URL patterns)
# ──────────────────────────────────────────────────────────


class TestURLNameCoverage:
    """Verify named URL patterns exist for all 22 expected endpoints."""

    EXPECTED_NAMES = {
        # Project CRUD (from SimpleRouter)
        "project-list",
        "project-detail",
        # FSM action endpoints (16)
        "project-submit",
        "project-accept-review",
        "project-approve",
        "project-observe",
        "project-return-to-draft",
        "project-reject",
        "project-resubmit",
        "project-start-execution",
        "project-suspend",
        "project-resume",
        "project-finalize",
        "project-initiate-closure",
        "project-close",
        "project-cancel",
        # Members
        "project-member-list",
        "project-member-detail",
        # Documents
        "project-document-list",
        "project-document-detail",
        # Observations (read-only)
        "project-observation-list",
        # State history (read-only)
        "project-state-log-list",
    }

    def test_all_expected_names_present(self):
        """All spec-defined URL names must exist in urlpatterns."""
        from django.urls.resolvers import URLPattern, URLResolver

        from apps.projects import urls

        def _collect_names(patterns):
            names = set()
            for p in patterns:
                if isinstance(p, URLResolver):
                    names.update(_collect_names(p.url_patterns))
                elif isinstance(p, URLPattern) and p.name:
                    names.add(p.name)
            return names

        names = _collect_names(urls.urlpatterns)

        for expected in self.EXPECTED_NAMES:
            assert expected in names, f"Missing URL name: {expected}"

    def test_all_expected_names_match_exactly(self):
        """URL names must match the expected set exactly."""
        from django.urls.resolvers import URLPattern, URLResolver

        from apps.projects import urls

        def _collect_names(patterns):
            names = set()
            for p in patterns:
                if isinstance(p, URLResolver):
                    names.update(_collect_names(p.url_patterns))
                elif isinstance(p, URLPattern) and p.name:
                    names.add(p.name)
            return names

        names = _collect_names(urls.urlpatterns)
        assert names == self.EXPECTED_NAMES, (
            f"Missing: {self.EXPECTED_NAMES - names}\n"
            f"Extra: {names - self.EXPECTED_NAMES}"
        )

    def test_22_total_url_names(self):
        """Exactly 22 URL names: 2 CRUD + 16 FSM + 2 members + 2 docs + 1 obs + 1 state_log."""
        from django.urls.resolvers import URLPattern, URLResolver

        from apps.projects import urls

        def _count_names(patterns):
            count = 0
            for p in patterns:
                if isinstance(p, URLResolver):
                    count += _count_names(p.url_patterns)
                elif isinstance(p, URLPattern) and p.name:
                    count += 1
            return count

        total = _count_names(urls.urlpatterns)
        assert total == 22, f"Expected 22 URL names, got {total}"


# ──────────────────────────────────────────────────────────
# Path structure
# ──────────────────────────────────────────────────────────


class TestPathStructure:
    """Verify URL path patterns follow the spec contract."""

    @staticmethod
    def _find_path(pattern_str, patterns):
        """Recursively search for a pattern substring in urlpatterns."""
        from django.urls.resolvers import URLPattern, URLResolver

        for p in patterns:
            if isinstance(p, URLResolver):
                if TestPathStructure._find_path(pattern_str, p.url_patterns):
                    return True
            elif isinstance(p, URLPattern):
                if pattern_str in str(p.pattern):
                    return True
        return False

    def test_project_base_patterns(self):
        """Base Project patterns must be in urlpatterns."""
        from apps.projects import urls

        assert self._find_path("projects", urls.urlpatterns)

    def test_project_detail_path(self):
        """Projects base path must be in urlpatterns."""
        from apps.projects import urls

        # The detail path pattern is generated by SimpleRouter; just verify
        # the 'projects' prefix is present and urlpatterns contain route entries.
        pattern_strs = [str(p.pattern) for p in urls.urlpatterns]
        combined = " ".join(pattern_strs)
        assert "projects" in combined

    def test_fsm_submit_endpoint(self):
        """submit/ endpoint must exist."""
        from apps.projects import urls

        assert self._find_path("submit/", urls.urlpatterns)

    def test_fsm_accept_review_endpoint(self):
        """accept_review/ endpoint must exist."""
        from apps.projects import urls

        assert self._find_path("accept_review/", urls.urlpatterns)

    def test_fsm_approve_endpoint(self):
        """approve/ endpoint must exist."""
        from apps.projects import urls

        assert self._find_path("approve/", urls.urlpatterns)

    def test_fsm_observe_endpoint(self):
        """observe/ endpoint must exist."""
        from apps.projects import urls

        assert self._find_path("observe/", urls.urlpatterns)

    def test_fsm_return_to_draft_endpoint(self):
        """return_to_draft/ endpoint must exist."""
        from apps.projects import urls

        assert self._find_path("return_to_draft/", urls.urlpatterns)

    def test_fsm_reject_endpoint(self):
        """reject/ endpoint must exist."""
        from apps.projects import urls

        assert self._find_path("reject/", urls.urlpatterns)

    def test_fsm_resubmit_endpoint(self):
        """resubmit/ endpoint must exist."""
        from apps.projects import urls

        assert self._find_path("resubmit/", urls.urlpatterns)

    def test_fsm_start_execution_endpoint(self):
        """start_execution/ endpoint must exist."""
        from apps.projects import urls

        assert self._find_path("start_execution/", urls.urlpatterns)

    def test_fsm_suspend_endpoint(self):
        """suspend/ endpoint must exist."""
        from apps.projects import urls

        assert self._find_path("suspend/", urls.urlpatterns)

    def test_fsm_resume_endpoint(self):
        """resume/ endpoint must exist."""
        from apps.projects import urls

        assert self._find_path("resume/", urls.urlpatterns)

    def test_fsm_finalize_endpoint(self):
        """finalize/ endpoint must exist."""
        from apps.projects import urls

        assert self._find_path("finalize/", urls.urlpatterns)

    def test_fsm_initiate_closure_endpoint(self):
        """initiate_closure/ endpoint must exist."""
        from apps.projects import urls

        assert self._find_path("initiate_closure/", urls.urlpatterns)

    def test_fsm_close_endpoint(self):
        """close/ endpoint must exist."""
        from apps.projects import urls

        assert self._find_path("close/", urls.urlpatterns)

    def test_fsm_cancel_endpoint(self):
        """cancel/ endpoint must exist."""
        from apps.projects import urls

        assert self._find_path("cancel/", urls.urlpatterns)

    def test_members_endpoint_exists(self):
        """members/ endpoint must exist in nested routes."""
        from apps.projects import urls

        assert self._find_path("members/", urls.urlpatterns)

    def test_members_detail_endpoint_exists(self):
        """members/<uuid:pk>/ endpoint must exist."""
        from apps.projects import urls

        assert self._find_path("members/<uuid:pk>", urls.urlpatterns)

    def test_documents_endpoint_exists(self):
        """documents/ endpoint must exist in nested routes."""
        from apps.projects import urls

        assert self._find_path("documents/", urls.urlpatterns)

    def test_documents_detail_endpoint_exists(self):
        """documents/<uuid:pk>/ endpoint must exist."""
        from apps.projects import urls

        assert self._find_path("documents/<uuid:pk>", urls.urlpatterns)

    def test_observations_endpoint_exists(self):
        """observations/ endpoint must exist in nested routes."""
        from apps.projects import urls

        assert self._find_path("observations/", urls.urlpatterns)

    def test_state_history_endpoint_exists(self):
        """state_history/ endpoint must exist in nested routes."""
        from apps.projects import urls

        assert self._find_path("state_history/", urls.urlpatterns)
