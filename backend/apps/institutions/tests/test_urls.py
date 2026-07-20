"""
Tests for institutions URL routing (Phase 3.4).

Verifies the URL pattern structure — nested routes, lifecycle endpoints,
and named URL patterns — without resolving views (viewsets created in Phase 4).

Note: URL resolution (resolve()/reverse()) requires viewsets to exist,
so those tests will be written in Phase 4 alongside view creation.
This file validates the URL configuration shape.
"""


# ──────────────────────────────────────────────────────────
# Module structure
# ──────────────────────────────────────────────────────────


class TestURLModuleExists:
    """Verify the urls module is importable and has expected shape."""

    def test_urls_module_imports(self):
        """urls.py must be importable as a Python module."""
        from apps.institutions import urls

        assert urls is not None

    def test_app_name_set(self):
        """app_name must be set for URL namespace resolution."""
        from apps.institutions import urls

        assert urls.app_name == "institutions"

    def test_router_registered(self):
        """SimpleRouter must be configured with Institution ViewSet."""
        from apps.institutions import urls

        assert hasattr(urls, "router")
        assert len(urls.router.registry) >= 1
        # First registry entry should be (prefix, viewset, basename)
        prefix, _viewset, basename = urls.router.registry[0]
        assert prefix == "institutions"
        assert basename == "institution"

    def test_urlpatterns_is_list(self):
        """urlpatterns must be a non-empty list."""
        from apps.institutions import urls

        assert isinstance(urls.urlpatterns, list)
        assert len(urls.urlpatterns) > 0


# ──────────────────────────────────────────────────────────
# URL name coverage
# ──────────────────────────────────────────────────────────


class TestURLNameCoverage:
    """Verify named URL patterns exist for all expected endpoints."""

    EXPECTED_NAMES = {
        # Institution (from router)
        "institution-list",
        "institution-detail",
        # Nested: sedes
        "institution-sede-list",
        "institution-sede-detail",
        # Nested: facultades
        "institution-facultad-list",
        "institution-facultad-detail",
        # Nested: centers
        "institution-center-list",
        "institution-center-detail",
        # Nested: groups
        "center-group-list",
        "center-group-detail",
        # Nested: lines
        "group-line-list",
        "group-line-detail",
        # Lifecycle: institution
        "institution-activate",
        "institution-deactivate",
        "institution-archive",
        # Lifecycle: sede
        "sede-activate",
        "sede-deactivate",
        "sede-archive",
        # Lifecycle: facultad
        "facultad-activate",
        "facultad-deactivate",
        "facultad-archive",
        # Lifecycle: center
        "center-activate",
        "center-deactivate",
        "center-archive",
        # Lifecycle: group
        "group-activate",
        "group-deactivate",
        "group-archive",
        # Lifecycle: line
        "line-activate",
        "line-deactivate",
        "line-archive",
    }

    def test_all_expected_names_present(self):
        """All spec-defined URL names must exist in urlpatterns."""
        from django.urls.resolvers import URLPattern, URLResolver

        from apps.institutions import urls

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

    def test_lifecycle_endpoints_count(self):
        """Must have exactly 18 lifecycle endpoints (6 entities × 3 transitions)."""
        from django.urls.resolvers import URLPattern, URLResolver

        from apps.institutions import urls

        def _count_lifecycle(patterns):
            count = 0
            for p in patterns:
                if isinstance(p, URLResolver):
                    count += _count_lifecycle(p.url_patterns)
                elif isinstance(p, URLPattern) and p.name:
                    if any(
                        suffix in (p.name or "") for suffix in ("activate", "deactivate", "archive")
                    ):
                        count += 1
            return count

        total = _count_lifecycle(urls.urlpatterns)
        assert total == 18, f"Expected 18 lifecycle endpoints, got {total}"


# ──────────────────────────────────────────────────────────
# Path structure
# ──────────────────────────────────────────────────────────


class TestPathStructure:
    """Verify URL path patterns follow the spec contract."""

    def test_institution_patterns_exist(self):
        """Base Institution patterns must be in urlpatterns."""
        from django.urls.resolvers import URLPattern, URLResolver

        from apps.institutions import urls

        def _find_path(pattern_str, patterns):
            for p in patterns:
                if isinstance(p, URLResolver):
                    if pattern_str in str(p.pattern):
                        return True
                elif isinstance(p, URLPattern):
                    if pattern_str in str(p.pattern):
                        return True
            return False

        # Check institution base route
        assert _find_path("institutions", urls.urlpatterns)

    def test_nested_institution_paths(self):
        """Nested routes exist under institutions/<uuid>/."""
        from apps.institutions import urls

        pattern_strs = [str(p.pattern) for p in urls.urlpatterns]
        combined = " ".join(pattern_strs)
        assert "institutions/<uuid:institution_pk>" in combined

    def test_nested_center_paths(self):
        """Nested routes exist under centers/<uuid>/."""
        from apps.institutions import urls

        pattern_strs = [str(p.pattern) for p in urls.urlpatterns]
        combined = " ".join(pattern_strs)
        assert "centers/<uuid:center_pk>" in combined

    def test_nested_group_paths(self):
        """Nested routes exist under groups/<uuid>/."""
        from apps.institutions import urls

        pattern_strs = [str(p.pattern) for p in urls.urlpatterns]
        combined = " ".join(pattern_strs)
        assert "groups/<uuid:group_pk>" in combined
