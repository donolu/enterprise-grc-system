from rest_framework import serializers

from .models import Asset, AssetReviewReminderLog


class AssetListSerializer(serializers.ModelSerializer):
    owner_display = serializers.SerializerMethodField()
    is_review_overdue = serializers.ReadOnlyField()
    days_until_review = serializers.ReadOnlyField()
    linked_risk_count = serializers.SerializerMethodField()
    linked_control_count = serializers.SerializerMethodField()
    linked_document_count = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = [
            'id', 'asset_id', 'name', 'asset_type', 'classification',
            'criticality', 'lifecycle_status', 'owner', 'owner_display',
            'owner_name', 'location', 'next_review_date',
            'is_review_overdue', 'days_until_review', 'linked_risk_count',
            'linked_control_count', 'linked_document_count',
        ]

    def get_owner_display(self, obj):
        if obj.owner:
            return obj.owner.get_full_name() or obj.owner.username
        return obj.owner_name

    def get_linked_risk_count(self, obj):
        return obj.linked_risks.count()

    def get_linked_control_count(self, obj):
        return obj.linked_controls.count()

    def get_linked_document_count(self, obj):
        return obj.linked_documents.count()


class AssetDetailSerializer(serializers.ModelSerializer):
    owner_display = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    is_review_overdue = serializers.ReadOnlyField()
    days_until_review = serializers.ReadOnlyField()

    class Meta:
        model = Asset
        fields = [
            'id', 'asset_id', 'name', 'asset_type', 'description',
            'classification', 'criticality', 'lifecycle_status', 'owner',
            'owner_display', 'owner_name', 'custodian', 'location', 'domain',
            'ip_address', 'mac_address', 'serial_number', 'manufacturer',
            'model', 'operating_system', 'version', 'acquisition_date',
            'last_seen_at', 'last_reviewed_at', 'next_review_date',
            'disposal_date', 'linked_risks', 'linked_controls',
            'linked_documents', 'source_path', 'source_sheet', 'source_row',
            'source_checksum', 'metadata', 'is_review_overdue',
            'days_until_review', 'created_by_username', 'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'source_path', 'source_sheet', 'source_row', 'source_checksum',
            'metadata', 'created_by_username', 'created_at', 'updated_at',
            'is_review_overdue', 'days_until_review',
        ]

    def get_owner_display(self, obj):
        if obj.owner:
            return obj.owner.get_full_name() or obj.owner.username
        return obj.owner_name

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class AssetImportSummarySerializer(serializers.Serializer):
    dry_run = serializers.BooleanField()
    importable_count = serializers.IntegerField(required=False)
    imported_count = serializers.IntegerField(required=False)
    updated_count = serializers.IntegerField(required=False)
    skipped_count = serializers.IntegerField()
    sheets = serializers.DictField(child=serializers.IntegerField())
    samples = serializers.ListField(required=False)


class AssetReviewReminderLogSerializer(serializers.ModelSerializer):
    asset_identifier = serializers.CharField(source='asset.asset_id', read_only=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = AssetReviewReminderLog
        fields = [
            'id', 'asset', 'asset_identifier', 'owner', 'owner_username',
            'reminder_type', 'review_date', 'sent_at', 'email_sent',
        ]
