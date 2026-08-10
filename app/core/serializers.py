"""
Serializers for core models including document upload functionality.
"""

from rest_framework import serializers
from .models import AuditEvent, Document, DocumentAccess, Tenant, User


class DocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for document uploads with file validation and metadata.
    """

    uploaded_by = serializers.StringRelatedField(read_only=True)
    file_url = serializers.URLField(read_only=True, allow_null=True)
    file_name = serializers.CharField(read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "description",
            "file",
            "file_url",
            "file_name",
            "uploaded_by",
            "uploaded_at",
            "updated_at",
            "file_size",
            "mime_type",
            "is_public",
        ]
        read_only_fields = ["uploaded_by", "uploaded_at", "updated_at", "file_size"]

    def validate_file(self, value):
        """Validate uploaded file."""
        # Check file size (max 100MB)
        max_size = 100 * 1024 * 1024  # 100MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size too large. Maximum allowed size is {max_size // (1024 * 1024)}MB"
            )

        # Check file extension (basic validation)
        allowed_extensions = [
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".txt",
            ".csv",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".zip",
        ]

        file_name = value.name.lower()
        if not any(file_name.endswith(ext) for ext in allowed_extensions):
            raise serializers.ValidationError(
                f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
            )

        return value

    def create(self, validated_data):
        """Create document with current user as uploader."""
        validated_data["uploaded_by"] = self.context["request"].user
        return super().create(validated_data)


class DocumentListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for document listings.
    """

    uploaded_by = serializers.StringRelatedField(read_only=True)
    file_name = serializers.CharField(read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "file_name",
            "uploaded_by",
            "uploaded_at",
            "file_size",
            "is_public",
        ]


class DocumentAccessSerializer(serializers.ModelSerializer):
    """
    Serializer for document access logs.
    """

    accessed_by = serializers.StringRelatedField(read_only=True)
    document_title = serializers.CharField(source="document.title", read_only=True)

    class Meta:
        model = DocumentAccess
        fields = [
            "id",
            "document",
            "document_title",
            "accessed_by",
            "accessed_at",
            "ip_address",
            "user_agent",
        ]
        read_only_fields = ["accessed_by", "accessed_at"]


class AuditEventSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = AuditEvent
        fields = ["id", "event", "user", "user_email", "details", "at"]
        read_only_fields = ["id", "event", "user", "user_email", "details", "at"]


class TenantEmailSettingsSerializer(serializers.ModelSerializer):
    sender_email_verified = serializers.SerializerMethodField()
    sender_email_verified_at = serializers.DateTimeField(
        source="email_sender_verified_at", read_only=True
    )

    class Meta:
        model = Tenant
        fields = [
            "email_sender_name",
            "email_sender_address",
            "email_reply_to",
            "sender_email_verified",
            "sender_email_verified_at",
        ]
        read_only_fields = ["sender_email_verified", "sender_email_verified_at"]

    def get_sender_email_verified(self, obj) -> bool:
        return bool(obj.email_sender_verified_at)


class TenantTaxProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = [
            "billing_country",
            "business_type",
            "tax_identifier",
            "tax_identifier_type",
            "tax_identifier_status",
            "tax_identifier_validated_at",
        ]
        read_only_fields = ["tax_identifier_status", "tax_identifier_validated_at"]

    def validate_billing_country(self, value):
        value = value.strip().upper()
        if len(value) != 2 or not value.isalpha():
            raise serializers.ValidationError("Use a two-letter ISO country code.")
        return value

    def validate(self, attrs):
        if attrs.get("tax_identifier") and not attrs.get(
            "tax_identifier_type", self.instance.tax_identifier_type
        ):
            raise serializers.ValidationError(
                {"tax_identifier_type": "Select a type for the tax identifier."}
            )
        return attrs

    def update(self, instance, validated_data):
        identity_fields = {"billing_country", "tax_identifier", "tax_identifier_type"}
        if identity_fields.intersection(validated_data):
            validated_data["tax_identifier_status"] = "unknown"
            validated_data["tax_identifier_validated_at"] = None
        return super().update(instance, validated_data)


class SenderVerificationResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    expires_at = serializers.DateTimeField(required=False)
    verified_at = serializers.DateTimeField(required=False)


class SenderVerificationConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(trim_whitespace=True)
