"""
Serializers for core models including document upload functionality.
"""

from rest_framework import serializers
from .models import Document, DocumentAccess, User


class DocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for document uploads with file validation and metadata.
    """
    uploaded_by = serializers.StringRelatedField(read_only=True)
    file_url = serializers.ReadOnlyField()
    file_name = serializers.ReadOnlyField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'title', 'description', 'file', 'file_url', 'file_name',
            'uploaded_by', 'uploaded_at', 'updated_at', 'file_size', 
            'mime_type', 'is_public'
        ]
        read_only_fields = ['uploaded_by', 'uploaded_at', 'updated_at', 'file_size']
    
    def validate_file(self, value):
        """Validate uploaded file."""
        # Check file size (max 100MB)
        max_size = 100 * 1024 * 1024  # 100MB
        if value.size > max_size:
            raise serializers.ValidationError(f"File size too large. Maximum allowed size is {max_size // (1024*1024)}MB")
        
        # Check file extension (basic validation)
        allowed_extensions = [
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.txt', '.csv', '.png', '.jpg', '.jpeg', '.gif', '.zip'
        ]
        
        file_name = value.name.lower()
        if not any(file_name.endswith(ext) for ext in allowed_extensions):
            raise serializers.ValidationError(
                f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        return value
    
    def create(self, validated_data):
        """Create document with current user as uploader."""
        validated_data['uploaded_by'] = self.context['request'].user
        return super().create(validated_data)


class DocumentListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for document listings.
    """
    uploaded_by = serializers.StringRelatedField(read_only=True)
    file_name = serializers.ReadOnlyField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'title', 'file_name', 'uploaded_by', 
            'uploaded_at', 'file_size', 'is_public'
        ]


class DocumentAccessSerializer(serializers.ModelSerializer):
    """
    Serializer for document access logs.
    """
    accessed_by = serializers.StringRelatedField(read_only=True)
    document_title = serializers.CharField(source='document.title', read_only=True)
    
    class Meta:
        model = DocumentAccess
        fields = [
            'id', 'document', 'document_title', 'accessed_by', 
            'accessed_at', 'ip_address', 'user_agent'
        ]
        read_only_fields = ['accessed_by', 'accessed_at']