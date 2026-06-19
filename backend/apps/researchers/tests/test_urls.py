"""
Tests for researchers URL routing (Phase 3.6).

Verifies the URL pattern structure — nested routes, named URL patterns —
without resolving views (viewsets created in Phase 4).

Note: URL resolution (reverse()) requires viewsets to exist, so those
tests will be written in Phase 4 alongside view creation.
This file validates URL configuration shape following the institutions pattern.

Strict TDD: this file is written BEFORE urls.py exists.
Expected failure: ModuleNotFoundError (urls.py not created yet).
"""


# ──────────────────────────────────────────────────────────
# Module structure
# ──────────────────────────────────────────────────────────


class TestURLModuleExists:
    """Verify the urls module is importable and has expected shape."""

    def test_urls_module_imports(self):
        """urls.py must be importable as a Python module."""
        from apps.researchers import urls

        assert urls is not None

    def test_app_name_set(self):
        """app_name must be set for URL namespace resolution."""
        from apps.researchers import urls

        assert urls.app_name == "researchers"

    def test_router_registered(self):
        """SimpleRouter must be configured with Researcher ViewSet."""
        from apps.researchers import urls

        assert hasattr(urls, "router")
        # Router should have at least 1 registry entry for researchers
        assert len(urls.router.registry) >= 1
        prefix, _viewset, basename = urls.router.registry[0]
        assert prefix == "researchers"
        assert basename == "researcher"

    def test_urlpatterns_is_list(self):
        """urlpatterns must be a non-empty list."""
        from apps.researchers import urls

        assert isinstance(urls.urlpatterns, list)
        assert len(urls.urlpatterns) > 0


# ──────────────────────────────────────────────────────────
# URL name coverage
# ──────────────────────────────────────────────────────────


class TestURLNameCoverage:
    """Verify named URL patterns exist for all expected endpoints."""

    EXPECTED_NAMES = {
        # Researcher (from SimpleRouter)
        "researcher-list",
        "researcher-detail",
        # Researcher custom actions
        "researcher-deactivate",
        # Nested: affiliations
        "researcher-affiliation-list",
        "researcher-affiliation-detail",
        "researcher-affiliation-set-primary",
        # Nested: external profiles
        "researcher-profile-list",
        "researcher-profile-detail",
        # Nested: attachments
        "researcher-attachment-list",
        "researcher-attachment-detail",
    }

    def test_all_expected_names_present(self):
        """All spec-defined URL names must exist in urlpatterns."""
        from django.urls.resolvers import URLPattern, URLResolver

        from apps.researchers import urls

        def _collect_names(patterns, prefix=""):
            names = set()
            for p in patterns:
                if isinstance(p, URLResolver):
                    names.update(_collect_names(p.url_patterns, prefix=p.app_name or ""))
                elif isinstance(p, URLPattern) and p.name:
                    names.add(p.name)
            return names

        names = _collect_names(urls.urlpatterns)

        for expected in self.EXPECTED_NAMES:
            assert expected in names, f"Missing URL name: {expected}"

    def test_no_extra_names(self):
        """URL names must match exactly the expected set (8 names from router + nested)."""
        from django.urls.resolvers import URLPattern, URLResolver

        from apps.researchers import urls

        def _collect_names(patterns, prefix=""):
            names = set()
            for p in patterns:
                if isinstance(p, URLResolver):
                    names.update(_collect_names(p.url_patterns, prefix=p.app_name or ""))
                elif isinstance(p, URLPattern) and p.name:
                    names.add(p.name)
            return names

        names = _collect_names(urls.urlpatterns)
        assert names == self.EXPECTED_NAMES, (
            f"Got extra/unexpected names: {names - self.EXPECTED_NAMES}"
        )


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

    def test_researcher_base_patterns(self):
        """Base Researcher patterns must be in urlpatterns."""
        from apps.researchers import urls

        assert self._find_path("researchers", urls.urlpatterns)

    def test_nested_researcher_paths(self):
        """Nested routes exist under researchers/<uuid>/."""
        from apps.researchers import urls

        pattern_strs = [str(p.pattern) for p in urls.urlpatterns]
        combined = " ".join(pattern_strs)
        assert "researchers/<uuid:researcher_pk>" in combined

    def test_nested_affiliations_endpoint(self):
        """affiliations/ endpoint exists in nested routes."""
        from apps.researchers import urls

        assert self._find_path("affiliations/", urls.urlpatterns)

    def test_nested_profiles_endpoint(self):
        """profiles/ endpoint exists in nested routes."""
        from apps.researchers import urls

        assert self._find_path("profiles/", urls.urlpatterns)

    def test_nested_attachments_endpoint(self):
        """attachments/ endpoint exists in nested routes."""
        from apps.researchers import urls

        assert self._find_path("attachments/", urls.urlpatterns)

    def test_10_total_url_names(self):
        """Exactly 10 URL names: 3 researcher + 3×2 nested + 1 set_primary."""
        from django.urls.resolvers import URLPattern, URLResolver

        from apps.researchers import urls

        def _count_names(patterns):
            count = 0
            for p in patterns:
                if isinstance(p, URLResolver):
                    count += _count_names(p.url_patterns)
                elif isinstance(p, URLPattern) and p.name:
                    count += 1
            return count

        total = _count_names(urls.urlpatterns)
        assert total == 10, f"Expected 10 URL names, got {total}"
