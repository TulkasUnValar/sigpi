"""
Unit tests for institutions serializers (Phase 3.3).

Covers all 6 ModelSerializers: Institution, Sede, Facultad,
ResearchCenter, ResearchGroup, ResearchLine.

Strict TDD: this file is written BEFORE serializers.py exists.
Expected failure: ModuleNotFoundError (serializers.py not created yet).
"""

import pytest

from apps.institutions.tests.conftest import (
    FacultadFactory,
    InstitutionFactory,
    ResearchCenterFactory,
    ResearchGroupFactory,
    ResearchLineFactory,
    SedeFactory,
)

# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────


def _make_serializer_data(factory, **overrides):
    """Build a dict suitable for serializer deserialization from a factory."""
    instance = factory.build(**overrides)
    data = {}
    for field in instance._meta.get_fields():
        if field.is_relation and field.many_to_many:
            continue
        if field.is_relation and field.many_to_one:
            continue
        name = field.name
        value = getattr(instance, name, None)
        if value is not None and name not in ("id", "created_at", "updated_at"):
            data[name] = value
    return data


# ──────────────────────────────────────────────────────────
# InstitutionSerializer
# ──────────────────────────────────────────────────────────


class TestInstitutionSerializer:
    """InstitutionSerializer: excludes institution_id, status read-only."""

    def test_valid_serialization(self):
        """Serialize an Institution model instance and verify output structure."""
        from apps.institutions.serializers import InstitutionSerializer

        inst = InstitutionFactory.build(id=None)  # not saved
        serialized = InstitutionSerializer(inst).data
        assert serialized["name"] == inst.name
        assert serialized["code"] == inst.code
        assert serialized["status"] == "active"
        assert "institution_id" not in serialized

    @pytest.mark.django_db
    def test_valid_deserialization_create(self):
        """Deserialize minimal valid data and confirm is_valid()."""
        from apps.institutions.serializers import InstitutionSerializer

        data = {"name": "New University", "code": "NU001"}
        serializer = InstitutionSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["name"] == "New University"
        assert serializer.validated_data["code"] == "NU001"

    @pytest.mark.django_db
    def test_status_field_read_only(self):
        """status must be ignored if provided during deserialization."""
        from apps.institutions.serializers import InstitutionSerializer

        data = {"name": "X", "code": "X01", "status": "archived"}
        serializer = InstitutionSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        # status should be ignored — default "active" from model
        assert "status" not in serializer.validated_data

    @pytest.mark.django_db
    def test_code_uniqueness_enforced(self):
        """Duplicate code — serializer rejects at is_valid() level (UniqueValidator)."""
        from apps.institutions.serializers import InstitutionSerializer

        InstitutionFactory(code="DUP001")
        data = {"name": "Another", "code": "DUP001"}
        serializer = InstitutionSerializer(data=data)
        assert not serializer.is_valid()
        assert "code" in serializer.errors

    def test_required_fields(self):
        """Missing name or code must fail validation."""
        from apps.institutions.serializers import InstitutionSerializer

        serializer = InstitutionSerializer(data={})
        assert not serializer.is_valid()
        assert "name" in serializer.errors
        assert "code" in serializer.errors


# ──────────────────────────────────────────────────────────
# SedeSerializer
# ──────────────────────────────────────────────────────────


class TestSedeSerializer:
    """SedeSerializer: institution read-only, status read-only."""

    def test_valid_serialization(self):
        """Sede serialize must show institution name and hide institution_id."""
        from apps.institutions.serializers import SedeSerializer

        inst = InstitutionFactory.build(id=None)
        sede = SedeFactory.build(id=None, institution=inst)
        serialized = SedeSerializer(sede).data
        assert serialized["name"] == sede.name
        assert serialized["code"] == sede.code
        assert serialized["status"] == "active"
        # institution is read-only — must be in output
        assert "institution" in serialized

    @pytest.mark.django_db
    def test_valid_deserialization_create(self):
        """Create a sede via serializer — institution is read-only, set on view side."""
        from apps.institutions.serializers import SedeSerializer

        inst = InstitutionFactory()
        data = {"name": "North Campus", "code": "NC01"}
        serializer = SedeSerializer(data=data, context={"institution": inst})
        assert serializer.is_valid(), serializer.errors

    @pytest.mark.django_db
    def test_code_unique_per_institution_constraint(self):
        """Duplicate (institution, code) — serializer passes, DB enforces."""
        from apps.institutions.serializers import SedeSerializer

        inst = InstitutionFactory()
        SedeFactory(institution=inst, code="CAMP01")
        data = {"name": "Another Campus", "code": "CAMP01"}
        serializer = SedeSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["code"] == "CAMP01"

    @pytest.mark.django_db
    def test_status_read_only(self):
        """status must be ignored on deserialization."""
        from apps.institutions.serializers import SedeSerializer

        data = {"name": "X", "code": "X01", "status": "archived"}
        serializer = SedeSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert "status" not in serializer.validated_data


# ──────────────────────────────────────────────────────────
# FacultadSerializer
# ──────────────────────────────────────────────────────────


class TestFacultadSerializer:
    """FacultadSerializer: institution + sede read-only, parent validation."""

    def test_valid_serialization(self):
        """Serialize must include parent info."""
        from apps.institutions.serializers import FacultadSerializer

        inst = InstitutionFactory.build(id=None)
        fac = FacultadFactory.build(id=None, institution=inst, sede=None)
        serialized = FacultadSerializer(fac).data
        assert serialized["name"] == fac.name
        assert serialized["code"] == fac.code
        assert serialized["status"] == "active"
        assert "institution" in serialized
        assert "sede" in serialized

    @pytest.mark.django_db
    def test_valid_deserialization(self):
        """Minimal valid data passes validation."""
        from apps.institutions.serializers import FacultadSerializer

        data = {"name": "Engineering", "code": "ENG01"}
        serializer = FacultadSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["name"] == "Engineering"

    @pytest.mark.django_db
    def test_parent_mismatch_rejected(self):
        """sede from different institution must be rejected by validate_sede."""
        from apps.institutions.serializers import FacultadSerializer

        inst1 = InstitutionFactory(code="I01")
        inst2 = InstitutionFactory(code="I02")
        wrong_sede = SedeFactory(institution=inst2, code="BAD")
        data = {
            "name": "Physics",
            "code": "PHY01",
            "sede": wrong_sede.pk,
        }
        # The institution is read-only; we pass it via context for validation
        serializer = FacultadSerializer(data=data, context={"institution": inst1})
        assert not serializer.is_valid()
        assert "sede" in serializer.errors

    def test_status_read_only(self):
        """status must be ignored — serializer handles no DB."""
        from apps.institutions.serializers import FacultadSerializer

        data = {"name": "X", "code": "X01", "status": "archived"}
        serializer = FacultadSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert "status" not in serializer.validated_data


# ──────────────────────────────────────────────────────────
# ResearchCenterSerializer
# ──────────────────────────────────────────────────────────


class TestResearchCenterSerializer:
    """ResearchCenterSerializer: institution, sede, facultad read-only."""

    def test_valid_serialization(self):
        """Serialize must include parent references."""
        from apps.institutions.serializers import ResearchCenterSerializer

        inst = InstitutionFactory.build(id=None)
        center = ResearchCenterFactory.build(id=None, institution=inst)
        serialized = ResearchCenterSerializer(center).data
        assert serialized["name"] == center.name
        assert serialized["code"] == center.code
        assert serialized["status"] == "active"
        assert "institution" in serialized
        assert "sede" in serialized
        assert "facultad" in serialized

    def test_contact_fields_present(self):
        """contact_email and contact_phone must be in serialized output."""
        from apps.institutions.serializers import ResearchCenterSerializer

        inst = InstitutionFactory.build(id=None)
        center = ResearchCenterFactory.build(
            id=None,
            institution=inst,
            contact_email="test@uni.edu",
            contact_phone="555-0100",
        )
        serialized = ResearchCenterSerializer(center).data
        assert serialized["contact_email"] == "test@uni.edu"
        assert serialized["contact_phone"] == "555-0100"

    @pytest.mark.django_db
    def test_valid_deserialization(self):
        """Minimal valid data passes."""
        from apps.institutions.serializers import ResearchCenterSerializer

        data = {"name": "AI Lab", "code": "AIL01"}
        serializer = ResearchCenterSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    @pytest.mark.django_db
    def test_status_read_only(self):
        """status must be ignored."""
        from apps.institutions.serializers import ResearchCenterSerializer

        data = {"name": "X", "code": "X01", "status": "archived"}
        serializer = ResearchCenterSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert "status" not in serializer.validated_data

    @pytest.mark.django_db
    def test_sede_mismatch_rejected(self):
        """sede from different institution must be rejected by validate_sede."""
        from apps.institutions.serializers import ResearchCenterSerializer

        inst1 = InstitutionFactory(code="I01")
        inst2 = InstitutionFactory(code="I02")
        wrong_sede = SedeFactory(institution=inst2, code="BAD")
        data = {
            "name": "Robotics",
            "code": "ROB01",
            "sede": wrong_sede.pk,
        }
        serializer = ResearchCenterSerializer(data=data, context={"institution": inst1})
        assert not serializer.is_valid()
        assert "sede" in serializer.errors

    @pytest.mark.django_db
    def test_facultad_mismatch_rejected(self):
        """facultad from different institution must be rejected by validate_facultad."""
        from apps.institutions.serializers import ResearchCenterSerializer

        inst1 = InstitutionFactory(code="I01")
        inst2 = InstitutionFactory(code="I02")
        wrong_facultad = FacultadFactory(institution=inst2, code="BAD")
        data = {
            "name": "AI Lab",
            "code": "AI01",
            "facultad": wrong_facultad.pk,
        }
        serializer = ResearchCenterSerializer(data=data, context={"institution": inst1})
        assert not serializer.is_valid()
        assert "facultad" in serializer.errors


# ──────────────────────────────────────────────────────────
# ResearchGroupSerializer
# ──────────────────────────────────────────────────────────


class TestResearchGroupSerializer:
    """ResearchGroupSerializer: institution + center read-only."""

    def test_valid_serialization(self):
        """Serialize must include parent info."""
        from apps.institutions.serializers import ResearchGroupSerializer

        inst = InstitutionFactory.build(id=None)
        center = ResearchCenterFactory.build(id=None, institution=inst)
        group = ResearchGroupFactory.build(id=None, institution=inst, center=center)
        serialized = ResearchGroupSerializer(group).data
        assert serialized["name"] == group.name
        assert serialized["code"] == group.code
        assert serialized["status"] == "active"
        assert "institution" in serialized
        assert "center" in serialized

    @pytest.mark.django_db
    def test_valid_deserialization(self):
        """Minimal valid data passes — center is set by view via save()."""
        from apps.institutions.serializers import ResearchGroupSerializer

        data = {"name": "NLP Group", "code": "NLP01"}
        serializer = ResearchGroupSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["name"] == "NLP Group"

    def test_status_read_only(self):
        """status must be ignored — center is read-only so no DB needed."""
        from apps.institutions.serializers import ResearchGroupSerializer

        data = {"name": "X", "code": "X01", "status": "archived"}
        serializer = ResearchGroupSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert "status" not in serializer.validated_data


# ──────────────────────────────────────────────────────────
# ResearchLineSerializer
# ──────────────────────────────────────────────────────────


class TestResearchLineSerializer:
    """ResearchLineSerializer: institution + group read-only."""

    def test_valid_serialization(self):
        """Serialize must include parent info."""
        from apps.institutions.serializers import ResearchLineSerializer

        inst = InstitutionFactory.build(id=None)
        center = ResearchCenterFactory.build(id=None, institution=inst)
        grp = ResearchGroupFactory.build(id=None, institution=inst, center=center)
        line = ResearchLineFactory.build(id=None, institution=inst, group=grp)

        serialized = ResearchLineSerializer(line).data
        assert serialized["name"] == line.name
        assert serialized["code"] == line.code
        assert serialized["status"] == "active"
        assert "institution" in serialized
        assert "group" in serialized

    @pytest.mark.django_db
    def test_valid_deserialization(self):
        """Minimal valid data passes — group is set by view via save()."""
        from apps.institutions.serializers import ResearchLineSerializer

        data = {"name": "Quantum Computing", "code": "QC01"}
        serializer = ResearchLineSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["name"] == "Quantum Computing"

    def test_status_read_only(self):
        """status must be ignored — group is read-only so no DB needed."""
        from apps.institutions.serializers import ResearchLineSerializer

        data = {"name": "X", "code": "X01", "status": "archived"}
        serializer = ResearchLineSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        assert "status" not in serializer.validated_data


# ──────────────────────────────────────────────────────────
# Cross-serializer: Status Read-Only Consistency
# ──────────────────────────────────────────────────────────


class TestStatusAcrossSerializers:
    """All 6 serializers must treat status as read-only."""

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "serializer_cls_name,data",
        [
            ("InstitutionSerializer", {"name": "T", "code": "T01", "status": "archived"}),
            ("SedeSerializer", {"name": "T", "code": "T01", "status": "archived"}),
            ("FacultadSerializer", {"name": "T", "code": "T01", "status": "archived"}),
            ("ResearchCenterSerializer", {"name": "T", "code": "T01", "status": "archived"}),
            ("ResearchGroupSerializer", {"name": "T", "code": "T01", "status": "archived"}),
            ("ResearchLineSerializer", {"name": "T", "code": "T01", "status": "archived"}),
        ],
    )
    def test_status_read_only_ignored(self, serializer_cls_name, data):
        """Every serializer must ignore status on input."""
        import apps.institutions.serializers as mod

        serializer_cls = getattr(mod, serializer_cls_name)
        serializer = serializer_cls(data=data)
        assert serializer.is_valid(), f"{serializer_cls_name}: {serializer.errors}"
        assert "status" not in serializer.validated_data, (
            f"{serializer_cls_name} should ignore status"
        )
