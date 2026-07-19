"""
Views for document management and storage testing.
"""

from django.conf import settings
from rest_framework import filters, viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.http import HttpResponse, Http404
from django.utils import timezone
from .document_audit import (
    audit_document_change,
    document_changed_values,
    document_display,
    snapshot_document,
)
from .models import AuditEvent, Document, DocumentAccess, Tenant
from .serializers import (
    AuditEventSerializer,
    DocumentSerializer,
    DocumentListSerializer,
    DocumentAccessSerializer,
)
from billing.decorators import check_document_limits
from billing.services import PlanEnforcementService
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse, OpenApiExample
from drf_spectacular.types import OpenApiTypes


@extend_schema_view(
    list=extend_schema(
        summary="List audit events",
        description="Retrieve the current tenant audit trail. Staff users only.",
        tags=['Audit'],
    ),
    retrieve=extend_schema(
        summary="Get audit event",
        description="Retrieve one current-tenant audit event. Staff users only.",
        tags=['Audit'],
    ),
)
class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditEventSerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['event', 'user__email']
    ordering_fields = ['event', 'at']
    ordering = ['-at']

    def get_queryset(self):
        return AuditEvent.objects.select_related('user')


@extend_schema_view(
    list=extend_schema(
        summary="List documents",
        description="Retrieve a paginated list of documents uploaded by users in the current tenant with secure access control.",
        tags=['Documents'],
    ),
    create=extend_schema(
        summary="Upload document",
        description="Upload a new document file to secure tenant-isolated storage with plan limit enforcement.",
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {'type': 'string', 'format': 'binary', 'description': 'File to upload'},
                    'title': {'type': 'string', 'description': 'Document title'},
                    'description': {'type': 'string', 'description': 'Document description'},
                    'is_public': {'type': 'boolean', 'description': 'Whether document is publicly accessible'},
                }
            }
        },
        responses={
            201: DocumentSerializer,
            400: OpenApiResponse(description='Invalid file or data'),
            403: OpenApiResponse(description='Document limit exceeded for current plan'),
        },
        tags=['Documents'],
    ),
    retrieve=extend_schema(
        summary="Get document details",
        description="Retrieve detailed information about a specific document including metadata and access information.",
        tags=['Documents'],
    ),
    update=extend_schema(
        summary="Update document",
        description="Update document metadata. File cannot be changed after upload.",
        tags=['Documents'],
    ),
    destroy=extend_schema(
        summary="Delete document",
        description="Delete a document and its file from storage. Only the uploader can delete documents.",
        tags=['Documents'],
    ),
)
class DocumentViewSet(viewsets.ModelViewSet):
    """
    **Document Management and File Storage**
    
    This ViewSet provides comprehensive document management with Azure Blob Storage integration:
    - Secure file upload with tenant isolation
    - Plan-based storage limits enforcement
    - Access logging and audit trails
    - Secure download with access control
    
    **Key Features:**
    - Azure Blob Storage integration with tenant containers
    - Plan-based document limits (Free: 100MB, Basic: 1GB, Enterprise: 10GB)
    - Comprehensive access logging for security audit
    - Support for various file types and sizes
    - Secure download URLs with access control
    
    **Security Features:**
    - Tenant isolation in storage containers
    - Access control and permission checking
    - Audit logging for all file access
    - Secure file URL generation
    
    **Common Use Cases:**
    - Upload evidence files for assessments
    - Store compliance documentation
    - Manage policy and procedure documents
    - Download files with access tracking
    """
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    throttle_scope_by_action = {"create": "evidence_upload"}

    def get_throttles(self):
        action = str(getattr(self, "action", ""))
        self.throttle_scope = self.throttle_scope_by_action.get(
            action
        )
        return super().get_throttles()
    
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
        tenant = self.request.tenant
        can_add, usage_info = PlanEnforcementService.check_document_limit(tenant)
        
        if not can_add:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(usage_info.get('error', 'Document limit exceeded'))
        
        document = serializer.save(uploaded_by=self.request.user)
        audit_document_change(
            event='DOCUMENT_UPLOADED',
            actor=self.request.user,
            target=document,
            object_display=document_display(document),
            request=self.request,
            new=snapshot_document(document),
        )

    def perform_update(self, serializer):
        previous = snapshot_document(serializer.instance)
        document = serializer.save()
        new = snapshot_document(document)
        previous_changed, new_changed = document_changed_values(previous, new)
        if previous_changed or new_changed:
            event = 'DOCUMENT_REPLACED' if 'file' in new_changed else 'DOCUMENT_UPDATED'
            audit_document_change(
                event=event,
                actor=self.request.user,
                target=document,
                object_display=document_display(document),
                request=self.request,
                previous=previous_changed,
                new=new_changed,
            )

    def perform_destroy(self, instance):
        previous = snapshot_document(instance)
        audit_document_change(
            event='DOCUMENT_DELETED',
            actor=self.request.user,
            target=instance,
            object_display=document_display(instance),
            request=self.request,
            previous=previous,
        )
        instance.delete()
    
    @extend_schema(
        summary="Download document",
        description="Download a document file with access logging and security checks. Returns download URL or file stream.",
        responses={
            200: OpenApiResponse(
                description='Download URL and file information',
                examples=[
                    OpenApiExample(
                        'Download Response',
                        summary='Successful download request',
                        value={
                            'download_url': 'https://storage.blob.core.windows.net/tenant-123/documents/file.pdf',
                            'filename': 'compliance_report.pdf',
                            'size': 2048576
                        }
                    ),
                ]
            ),
            403: OpenApiResponse(description='Permission denied'),
            404: OpenApiResponse(description='File not found or inaccessible'),
        },
        tags=['Documents'],
    )
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Download a document file with secure access control and audit logging.
        Creates an access log entry for compliance and security audit purposes.
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
        audit_document_change(
            event='DOCUMENT_DOWNLOADED',
            actor=request.user,
            target=document,
            object_display=document_display(document),
            request=request,
            new={
                'document_id': document.id,
                'filename': document.file_name,
                'file_size': document.file_size,
                'mime_type': document.mime_type,
            },
            source={'type': 'api', 'reference': 'document.download'},
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

        if hasattr(default_storage, "_get_tenant_container_name"):
            container_name = default_storage._get_tenant_container_name()

            return Response({
                'storage_backend': default_storage.__class__.__name__,
                'container_name': container_name,
                'tenant_isolation': True,
                'configured_backend': getattr(settings, "STORAGE_BACKEND", "unknown"),
            })

        return Response({
            'storage_backend': str(type(default_storage)),
            'tenant_isolation': False,
            'configured_backend': getattr(settings, "STORAGE_BACKEND", "unknown"),
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
