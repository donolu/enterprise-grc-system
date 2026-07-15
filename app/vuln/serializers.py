from rest_framework import serializers

from .models import ScanJob, ScanSchedule, ScanTarget, VulnerabilityFinding
from .services import TargetValidationError, validate_scan_target_address


class ScanTargetSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source='owner.email', read_only=True)

    class Meta:
        model = ScanTarget
        fields = [
            'id', 'name', 'target_type', 'address', 'status', 'owner',
            'owner_email', 'tags', 'metadata', 'created_by', 'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def validate_address(self, value):
        try:
            return validate_scan_target_address(value)
        except TargetValidationError as exc:
            raise serializers.ValidationError(str(exc)) from exc


class ScanScheduleSerializer(serializers.ModelSerializer):
    target_name = serializers.CharField(source='target.name', read_only=True)

    class Meta:
        model = ScanSchedule
        fields = [
            'id', 'target', 'target_name', 'name', 'frequency', 'is_active',
            'next_run_at', 'last_run_at', 'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'last_run_at', 'created_at', 'updated_at']


class ScanJobSerializer(serializers.ModelSerializer):
    target_name = serializers.CharField(source='target.name', read_only=True)
    target_address = serializers.CharField(source='target.address', read_only=True)

    class Meta:
        model = ScanJob
        fields = [
            'id', 'target', 'target_name', 'target_address', 'schedule', 'scanner',
            'status', 'requested_by', 'started_at', 'finished_at', 'error_message',
            'findings_count', 'scan_config', 'raw_summary', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'requested_by', 'started_at', 'finished_at', 'error_message',
            'findings_count', 'raw_summary', 'created_at', 'updated_at',
        ]


class VulnerabilityFindingSerializer(serializers.ModelSerializer):
    target_name = serializers.CharField(source='target.name', read_only=True)
    risk_id = serializers.CharField(source='risk.risk_id', read_only=True)
    risk_action_id = serializers.CharField(source='risk_action.action_id', read_only=True)

    class Meta:
        model = VulnerabilityFinding
        fields = [
            'id', 'target', 'target_name', 'job', 'fingerprint', 'scanner_name',
            'scanner_finding_id', 'template_id', 'title', 'severity', 'description',
            'remediation', 'matched_at', 'cve', 'cvss_score', 'evidence', 'status',
            'risk', 'risk_id', 'risk_action', 'risk_action_id', 'first_seen_at',
            'last_seen_at', 'resolved_at', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'fingerprint', 'scanner_name', 'scanner_finding_id', 'template_id',
            'title', 'severity', 'description', 'remediation', 'matched_at', 'cve',
            'cvss_score', 'evidence', 'risk', 'risk_id', 'risk_action',
            'risk_action_id', 'first_seen_at', 'last_seen_at', 'resolved_at',
            'created_at', 'updated_at',
        ]
