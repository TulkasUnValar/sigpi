"""
DRF Serializers for the Reports / Informes module (§6.6).

PreviewSerializer returns {"html": "..."} for the preview endpoint (RF-056).

Design reference: openspec/changes/reports/design.md
"""

from rest_framework import serializers


class PreviewSerializer(serializers.Serializer):
    """Serializer for the HTML preview response — returns {"html": "..."}."""

    html = serializers.CharField()
