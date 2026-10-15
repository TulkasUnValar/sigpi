"""
Serializers for dashboard summary endpoint.

Defines the response schema for the 14 indicators and chart data.
"""

from rest_framework import serializers


class ProjectByCenterSerializer(serializers.Serializer):
    """Serializer for IND-002: projects grouped by research center."""

    center_id = serializers.UUIDField()
    name = serializers.CharField()
    count = serializers.IntegerField()


class ProjectByStatusSerializer(serializers.Serializer):
    """Serializer for IND-003: projects grouped by status."""

    status = serializers.CharField()
    count = serializers.IntegerField()


class ProductsByProjectSerializer(serializers.Serializer):
    """Serializer for IND-010: products grouped by project."""

    project_id = serializers.UUIDField()
    project_title = serializers.CharField()
    count = serializers.IntegerField()


class ProductsByResearcherSerializer(serializers.Serializer):
    """Serializer for IND-011: products grouped by researcher."""

    researcher_id = serializers.UUIDField()
    researcher_name = serializers.CharField()
    count = serializers.IntegerField()


class ProfileCompletenessSerializer(serializers.Serializer):
    """Serializer for IND-012: researcher profile completeness metrics."""

    total = serializers.IntegerField()
    complete = serializers.IntegerField()
    rate = serializers.FloatField()


class BudgetChartSerializer(serializers.Serializer):
    """Serializer for budget chart data."""

    approved = serializers.CharField()
    executed = serializers.CharField()
    balance = serializers.CharField()


class ProgressReportsChartSerializer(serializers.Serializer):
    """Serializer for progress reports chart data."""

    pending = serializers.IntegerField()
    observed = serializers.IntegerField()
    approved = serializers.IntegerField()


class ChartsSerializer(serializers.Serializer):
    """Serializer for all chart data sections."""

    projects_by_status = ProjectByStatusSerializer(many=True)
    projects_by_center = ProjectByCenterSerializer(many=True)
    budget = BudgetChartSerializer()
    progress_reports = ProgressReportsChartSerializer()


class IndicatorsSerializer(serializers.Serializer):
    """Serializer for all 14 dashboard indicators."""

    IND_001 = serializers.IntegerField(source="IND-001", help_text="Total proyectos activos")
    IND_002 = ProjectByCenterSerializer(
        many=True, source="IND-002", help_text="Proyectos por centro"
    )
    IND_003 = ProjectByStatusSerializer(
        many=True, source="IND-003", help_text="Proyectos por estado"
    )
    IND_004 = serializers.IntegerField(source="IND-004", help_text="Avances pendientes")
    IND_005 = serializers.IntegerField(source="IND-005", help_text="Avances observados")
    IND_006 = serializers.FloatField(source="IND-006", help_text="Cumplimiento de reportes (%)")
    IND_007 = serializers.CharField(source="IND-007", help_text="Presupuesto aprobado total")
    IND_008 = serializers.CharField(source="IND-008", help_text="Presupuesto ejecutado")
    IND_009 = serializers.CharField(source="IND-009", help_text="Saldo presupuestal")
    IND_010 = ProductsByProjectSerializer(
        many=True, source="IND-010", help_text="Productos por proyecto (top 10)"
    )
    IND_011 = ProductsByResearcherSerializer(
        many=True, source="IND-011", help_text="Productos por investigador (top 10)"
    )
    IND_012 = ProfileCompletenessSerializer(
        source="IND-012", help_text="Perfiles de investigadores completos"
    )
    IND_013 = serializers.IntegerField(source="IND-013", help_text="Convocatorias abiertas")
    IND_014 = serializers.IntegerField(
        source="IND-014", help_text="Proyectos en convocatorias externas"
    )


class DashboardSummarySerializer(serializers.Serializer):
    """
    Top-level serializer for the dashboard summary response.

    Contains:
    - indicators: 14 computed metrics (IND-001 to IND-014)
    - charts: pre-aggregated data for frontend charts
    """

    indicators = IndicatorsSerializer()
    charts = ChartsSerializer()

    def to_representation(self, instance):
        """
        Convert indicator keys from underscores (IND_001) to hyphens (IND-001)
        to match the API contract and service layer output.
        """
        data = super().to_representation(instance)

        # Convert indicator keys from IND_001 to IND-001
        if "indicators" in data:
            indicators = data["indicators"]
            converted_indicators = {}
            for key, value in indicators.items():
                # Convert IND_001 to IND-001
                new_key = key.replace("_", "-")
                converted_indicators[new_key] = value
            data["indicators"] = converted_indicators

        return data
