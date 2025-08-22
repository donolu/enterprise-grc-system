"""
Views for document management and Azure Blob Storage testing.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import HttpResponse, Http404
from django.utils import timezone
from .models import Document, DocumentAccess, Tenant
from .serializers import DocumentSerializer, DocumentListSerializer, DocumentAccessSerializer
from billing.decorators import check_document_limits
from billing.services import PlanEnforcementService


class DocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for document upload and management.
    Demonstrates Azure Blob Storage integration with tenant isolation.
    """
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        """Return documents for the current tenant only."""
        return Document.objects.all()  # Tenant isolation handled by schema
    
    def get_serializer_class(self):
        """Use different serializers for different actions."""
        if self.action == 'list':
            return DocumentListSerializer
        return DocumentSerializer
    
    def perform_create(self, serializer):
        """Save document with current user as uploader."""
        # Check document limits before creating
        tenant = Tenant.objects.get(schema_name=self.request.tenant.schema_name)
        can_add, usage_info = PlanEnforcementService.check_document_limit(tenant)
        
        if not can_add:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(usage_info.get('error', 'Document limit exceeded'))
        
        serializer.save(uploaded_by=self.request.user)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Download a document file.
        Creates an access log entry for audit purposes.
        """
        document = self.get_object()
        
        # Check permissions
        if not document.is_public and document.uploaded_by != request.user:
            # In a real app, you might check group permissions here
            pass
        
        # Log the access
        DocumentAccess.objects.create(
            document=document,
            accessed_by=request.user,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        try:
            # For Azure Blob Storage, redirect to the blob URL
            # In production, you might want to generate a SAS token for secure access
            file_url = document.file.url
            
            # For direct download, you could also stream the file content:
            # response = HttpResponse(document.file.read(), content_type='application/octet-stream')
            # response['Content-Disposition'] = f'attachment; filename="{document.file_name}"'
            # return response
            
            # For now, return the file URL for client-side download
            return Response({
                'download_url': file_url,
                'filename': document.file_name,
                'size': document.file_size
            })
            
        except Exception as e:
            return Response(
                {'error': 'File not found or inaccessible'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def access_logs(self, request, pk=None):
        """Get access logs for a document."""
        document = self.get_object()
        
        # Only allow document owner to view access logs
        if document.uploaded_by != request.user:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        logs = DocumentAccess.objects.filter(document=document)
        serializer = DocumentAccessSerializer(logs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def storage_info(self, request):
        """
        Get information about the storage backend and tenant container.
        Useful for testing and debugging.
        """
        from django.core.files.storage import default_storage
        from core.storage import TenantAwareBlobStorage
        
        if isinstance(default_storage, TenantAwareBlobStorage):
            container_name = default_storage._get_tenant_container_name()
            
            return Response({
                'storage_backend': 'TenantAwareBlobStorage',
                'container_name': container_name,
                'connection_string': 'Configured' if default_storage.connection_string else 'Not configured',
                'tenant_isolation': True
            })
        else:
            return Response({
                'storage_backend': str(type(default_storage)),
                'tenant_isolation': False
            })
    
    @action(detail=False, methods=['get'])
    def plan_usage(self, request):
        """
        Get current plan usage and limits for the tenant.
        """
        try:
            tenant = Tenant.objects.get(schema_name=request.tenant.schema_name)
            usage_summary = PlanEnforcementService.get_plan_usage_summary(tenant)
            return Response(usage_summary)
        except Exception as e:
            return Response(
                {'error': 'Failed to fetch plan usage'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip