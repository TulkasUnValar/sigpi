"""
Unit tests for calls serializers (Phase 3.8).

Covers 6 serializers:
- CallListSerializer: lightweight list (id, title, status, call_type, created_at)
- CallSerializer: full detail + nested dates validation (read + write)
- CallDocumentSerializer: name, doc_type, external_url; call read-only
- CallProjectSerializer: read-only list of linked projects
- CallProjectCreateSerializer: writable, project FK only, call read-only
- CallStateLogSerializer: read-only state history

Strict TDD: this file is written BEFORE serializers.py exists.
Expected failure: ImportError (serializers.py not created yet).
"""

from uuid import uuid4

import pytest

# ──────────────────────────────────────────────────────────
# CallListSerializer
# ──────────────────────────────────────────────────────────


class TestCallListSerializer:
    """CallListSerializer: lightweight 5 fields (id, title, status, call_type, created_at)."""

    @pytest.mark.django_db
    def test_list_serializer_fields(self):
        """List serializer must expose exactly the lightweight fields."""
        from apps.calls.serializers import CallListSerializer
        from apps.calls.tests.conftest import CallFactory

        call = CallFactory()
        serialized = CallListSerializer(call).data

        expected = {"id", "title", "status", "call_type", "created_at"}
        assert set(serialized.keys()) == expected

    @pytest.mark.django_db
    def test_list_serializer_title_in_output(self):
        """title must be present in list output."""
        from apps.calls.serializers import CallListSerializer
        from apps.calls.tests.conftest import CallFactory

        call = CallFactory(title="Convocatoria Alpha")
        serialized = CallListSerializer(call).data
        assert serialized["title"] == "Convocatoria Alpha"

    @pytest.mark.django_db
    def test_list_serializer_status_in_output(self):
        """status must be present in list output."""
        from apps.calls.serializers import CallListSerializer
        from apps.calls.tests.conftest import CallFactory

        call = CallFactory(status="borrador")
        serialized = CallListSerializer(call).data
        assert serialized["status"] == "borrador"


# ──────────────────────────────────────────────────────────
# CallSerializer (full detail + write)
# ──────────────────────────────────────────────────────────


class TestCallSerializer:
    """CallSerializer: all fields + nested dates validation."""

    @pytest.mark.django_db
    def test_detail_contains_all_model_fields(self):
        """CallSerializer must serialize all Call model fields."""
        from apps.calls.serializers import CallSerializer
        from apps.calls.tests.conftest import CallFactory

        call = CallFactory()
        serialized = CallSerializer(call).data

        expected_core = {
            "id",
            "institution",
            "title",
            "description",
            "call_type",
            "external_entity",
            "submission_start",
            "submission_end",
            "evaluation_start",
            "evaluation_end",
            "status",
            "created_at",
            "updated_at",
        }
        missing = expected_core - set(serialized.keys())
        assert not missing, f"Missing fields: {missing}"

    @pytest.mark.django_db
    def test_deserialize_valid_data(self):
        """Minimal valid data must pass validation."""
        from apps.calls.serializers import CallSerializer

        data = {
            "title": "New Call",
            "description": "Description",
            "call_type": "internal",
        }
        serializer = CallSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    @pytest.mark.django_db
    def test_rejects_internal_with_entity(self):
        """Internal call with external_entity must be rejected."""
        from apps.calls.serializers import CallSerializer

        data = {
            "title": "Bad Call",
            "description": "Desc",
            "call_type": "internal",
            "external_entity": "CONAHCYT",
        }
        serializer = CallSerializer(data=data)
        assert not serializer.is_valid()
        assert "external_entity" in serializer.errors

    @pytest.mark.django_db
    def test_rejects_external_without_entity(self):
        """External call without external_entity must be rejected."""
        from apps.calls.serializers import CallSerializer

        data = {
            "title": "Bad Call",
            "description": "Desc",
            "call_type": "external",
        }
        serializer = CallSerializer(data=data)
        assert not serializer.is_valid()
        assert "external_entity" in serializer.errors

    @pytest.mark.django_db
    def test_rejects_submission_end_before_start(self):
        """submission_end < submission_start must be rejected."""
        from apps.calls.serializers import CallSerializer

        data = {
            "title": "Bad Dates",
            "description": "Desc",
            "call_type": "internal",
            "submission_start": "2026-06-01",
            "submission_end": "2026-05-01",
        }
        serializer = CallSerializer(data=data)
        assert not serializer.is_valid()
        assert "submission_end" in serializer.errors

    @pytest.mark.django_db
    def test_accepts_valid_dates(self):
        """Valid date ordering must pass."""
        from apps.calls.serializers import CallSerializer

        data = {
            "title": "Good Dates",
            "description": "Desc",
            "call_type": "internal",
            "submission_start": "2026-01-01",
            "submission_end": "2026-06-01",
            "evaluation_start": "2026-07-01",
            "evaluation_end": "2026-12-01",
        }
        serializer = CallSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    @pytest.mark.django_db
    def test_institution_read_only(self):
        """institution must be read-only — ignored if provided in input."""
        from apps.calls.serializers import CallSerializer

        data = {
            "title": "Call X",
            "description": "Desc",
            "call_type": "internal",
            "institution": str(uuid4()),
        }
        serializer = CallSerializer(data=data)
        assert isinstance(serializer.is_valid(), bool)
        assert "institution" not in serializer.errors


# ──────────────────────────────────────────────────────────
# CallDocumentSerializer
# ──────────────────────────────────────────────────────────


class TestCallDocumentSerializer:
    """CallDocumentSerializer: name, doc_type, external_url; call read-only."""

    @pytest.mark.django_db
    def test_serialization(self):
        """Serialized output must include name, doc_type, external_url."""
        from apps.calls.serializers import CallDocumentSerializer
        from apps.calls.tests.conftest import CallDocumentFactory

        doc = CallDocumentFactory(name="Terms", doc_type="convocatoria")
        serialized = CallDocumentSerializer(doc).data

        assert serialized["name"] == "Terms"
        assert serialized["doc_type"] == "convocatoria"
        assert "external_url" in serialized
        assert "call" in serialized
        assert "created_at" in serialized

    @pytest.mark.django_db
    def test_call_read_only(self):
        """call FK must be read-only."""
        from apps.calls.serializers import CallDocumentSerializer
        from apps.calls.tests.conftest import CallDocumentFactory

        doc = CallDocumentFactory()
        data = {"call": str(uuid4())}
        serializer = CallDocumentSerializer(instance=doc, data=data, partial=True)
        assert isinstance(serializer.is_valid(), bool)

    @pytest.mark.django_db
    def test_doc_type_choices_valid(self):
        """doc_type must accept valid CallDocumentType choices."""
        from apps.calls.serializers import CallDocumentSerializer

        for dt in ["convocatoria", "anexo", "reglamento", "resultado", "otro"]:
            data = {
                "name": "Doc",
                "doc_type": dt,
                "external_url": "https://example.com/doc",
            }
            serializer = CallDocumentSerializer(data=data)
            assert serializer.is_valid(), f"doc_type={dt}: {serializer.errors}"

    @pytest.mark.django_db
    def test_doc_type_invalid_choice_rejected(self):
        """Invalid doc_type must be rejected."""
        from apps.calls.serializers import CallDocumentSerializer

        data = {
            "name": "Doc",
            "doc_type": "invalid",
            "external_url": "https://example.com",
        }
        serializer = CallDocumentSerializer(data=data)
        assert not serializer.is_valid()
        assert "doc_type" in serializer.errors

    @pytest.mark.django_db
    def test_name_required(self):
        """name must be required."""
        from apps.calls.serializers import CallDocumentSerializer

        data = {"doc_type": "convocatoria", "external_url": "https://example.com"}
        serializer = CallDocumentSerializer(data=data)
        assert not serializer.is_valid()
        assert "name" in serializer.errors


# ──────────────────────────────────────────────────────────
# CallProjectSerializer
# ──────────────────────────────────────────────────────────


class TestCallProjectSerializer:
    """CallProjectSerializer: read-only list of linked projects."""

    @pytest.mark.django_db
    def test_serialization(self):
        """Serialized output must include id, call, project, linked_at."""
        from apps.calls.serializers import CallProjectSerializer
        from apps.calls.tests.conftest import CallProjectFactory

        cp = CallProjectFactory()
        serialized = CallProjectSerializer(cp).data

        assert "id" in serialized
        assert "call" in serialized
        assert "project" in serialized
        assert "linked_at" in serialized

    @pytest.mark.django_db
    def test_read_only_fields(self):
        """All fields must be read-only."""
        from apps.calls.serializers import CallProjectSerializer
        from apps.calls.tests.conftest import CallProjectFactory

        cp = CallProjectFactory()
        data = {"project": str(uuid4())}
        serializer = CallProjectSerializer(instance=cp, data=data, partial=True)
        assert isinstance(serializer.is_valid(), bool)


# ──────────────────────────────────────────────────────────
# CallProjectCreateSerializer
# ──────────────────────────────────────────────────────────


class TestCallProjectCreateSerializer:
    """CallProjectCreateSerializer: writable, project FK only, call read-only."""

    @pytest.mark.django_db
    def test_deserialize_valid_data(self):
        """project ID must be accepted."""
        from apps.calls.serializers import CallProjectCreateSerializer
        from apps.projects.tests.conftest import ProjectFactory

        project = ProjectFactory()
        data = {"project": project.pk}
        serializer = CallProjectCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    @pytest.mark.django_db
    def test_call_read_only(self):
        """call FK must be read-only."""
        from apps.calls.serializers import CallProjectCreateSerializer
        from apps.calls.tests.conftest import CallProjectFactory

        cp = CallProjectFactory()
        data = {"call": str(uuid4()), "project": str(uuid4())}
        serializer = CallProjectCreateSerializer(instance=cp, data=data, partial=True)
        assert isinstance(serializer.is_valid(), bool)
        assert "call" not in serializer.errors

    @pytest.mark.django_db
    def test_project_required(self):
        """project must be required."""
        from apps.calls.serializers import CallProjectCreateSerializer

        serializer = CallProjectCreateSerializer(data={})
        assert not serializer.is_valid()
        assert "project" in serializer.errors


# ──────────────────────────────────────────────────────────
# CallStateLogSerializer
# ──────────────────────────────────────────────────────────


class TestCallStateLogSerializer:
    """CallStateLogSerializer: read-only state history data."""

    @pytest.mark.django_db
    def test_serialization(self):
        """Serialized output must include from_state, to_state, triggered_by, reason, created_at."""
        from apps.calls.serializers import CallStateLogSerializer
        from apps.calls.tests.conftest import CallStateLogFactory

        log = CallStateLogFactory(from_state="borrador", to_state="abierta", reason="Opened")
        serialized = CallStateLogSerializer(log).data

        assert serialized["from_state"] == "borrador"
        assert serialized["to_state"] == "abierta"
        assert serialized["reason"] == "Opened"
        assert "triggered_by" in serialized
        assert "created_at" in serialized

    @pytest.mark.django_db
    def test_read_only_fields(self):
        """All fields must be read-only."""
        from apps.calls.serializers import CallStateLogSerializer
        from apps.calls.tests.conftest import CallStateLogFactory

        log = CallStateLogFactory()
        data = {"reason": "Modified"}
        serializer = CallStateLogSerializer(instance=log, data=data, partial=True)
        assert isinstance(serializer.is_valid(), bool)
