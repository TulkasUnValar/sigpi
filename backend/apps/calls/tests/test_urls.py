"""
Tests for calls URL routing (Phase 3.12).

Verifies URL pattern structure — named URL patterns, path structure.

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
        from apps.calls import urls

        assert urls is not None

    def test_app_name_set(self):
        """app_name must be set for URL namespace resolution."""
        from apps.calls import urls

        assert urls.app_name == "calls"

    def test_router_registered(self):
        """SimpleRouter must be configured with Call ViewSet."""
        from apps.calls import urls

        assert hasattr(urls, "router")
        assert len(urls.router.registry) >= 1
        prefix, _viewset, basename = urls.router.registry[0]
        assert prefix == "calls"
        assert basename == "call"

    def test_urlpatterns_is_list(self):
        """urlpatterns must be a non-empty list."""
        from apps.calls import urls

        assert isinstance(urls.urlpatterns, list)
        assert len(urls.urlpatterns) > 0


# ──────────────────────────────────────────────────────────
# URL name coverage
# ──────────────────────────────────────────────────────────


class TestURLNameCoverage:
    """Verify named URL patterns exist for all expected endpoints."""

    EXPECTED_NAMES = {
        # Call CRUD (from SimpleRouter)
        "call-list",
        "call-detail",
        # FSM action endpoints (5)
        "call-open-call",
        "call-close-call",
        "call-start-evaluation",
        "call-publish-results",
        "call-archive",
        # Documents
        "call-document-list",
        "call-document-detail",
        # Projects
        "call-project-list",
        "call-project-detail",
        # State history (read-only)
        "call-state-log-list",
    }

    def test_all_expected_names_present(self):
        """All spec-defined URL names must exist in urlpatterns."""
        from django.urls.resolvers import URLPattern, URLResolver

        from apps.calls import urls

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

        from apps.calls import urls

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
            f"Missing: {self.EXPECTED_NAMES - names}\nExtra: {names - self.EXPECTED_NAMES}"
        )

    def test_12_total_url_names(self):
        """Exactly 12 URL names."""
        from django.urls.resolvers import URLPattern, URLResolver

        from apps.calls import urls

        def _count_names(patterns):
            count = 0
            for p in patterns:
                if isinstance(p, URLResolver):
                    count += _count_names(p.url_patterns)
                elif isinstance(p, URLPattern) and p.name:
                    count += 1
            return count

        total = _count_names(urls.urlpatterns)
        assert total == 12, f"Expected 12 URL names, got {total}"


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

    def test_calls_base_patterns(self):
        """Base calls patterns must be in urlpatterns."""
        from apps.calls import urls

        assert self._find_path("calls", urls.urlpatterns)

    def test_fsm_open_call_endpoint(self):
        """open_call/ endpoint must exist."""
        from apps.calls import urls

        assert self._find_path("open_call/", urls.urlpatterns)

    def test_fsm_close_call_endpoint(self):
        """close_call/ endpoint must exist."""
        from apps.calls import urls

        assert self._find_path("close_call/", urls.urlpatterns)

    def test_fsm_start_evaluation_endpoint(self):
        """start_evaluation/ endpoint must exist."""
        from apps.calls import urls

        assert self._find_path("start_evaluation/", urls.urlpatterns)

    def test_fsm_publish_results_endpoint(self):
        """publish_results/ endpoint must exist."""
        from apps.calls import urls

        assert self._find_path("publish_results/", urls.urlpatterns)

    def test_fsm_archive_endpoint(self):
        """archive/ endpoint must exist."""
        from apps.calls import urls

        assert self._find_path("archive/", urls.urlpatterns)

    def test_documents_endpoint_exists(self):
        """documents/ endpoint must exist in nested routes."""
        from apps.calls import urls

        assert self._find_path("documents/", urls.urlpatterns)

    def test_documents_detail_endpoint_exists(self):
        """documents/<uuid:pk>/ endpoint must exist."""
        from apps.calls import urls

        assert self._find_path("documents/<uuid:pk>", urls.urlpatterns)

    def test_projects_endpoint_exists(self):
        """projects/ endpoint must exist in nested routes."""
        from apps.calls import urls

        assert self._find_path("projects/", urls.urlpatterns)

    def test_projects_detail_endpoint_exists(self):
        """projects/<uuid:pk>/ endpoint must exist."""
        from apps.calls import urls

        assert self._find_path("projects/<uuid:pk>", urls.urlpatterns)

    def test_state_history_endpoint_exists(self):
        """state_history/ endpoint must exist in nested routes."""
        from apps.calls import urls

        assert self._find_path("state_history/", urls.urlpatterns)
