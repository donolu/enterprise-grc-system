"""
Vendor Management Views

Comprehensive API views for vendor management including CRUD operations,
filtering, search, and bulk operations with proper tenant isolation.
"""

from django.shortcuts import get_object_or_404
from django.db.models import Count, Q, Avg, Sum, F
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from decimal import Decimal

from .models import Vendor, VendorCategory, VendorContact, VendorService, VendorNote, VendorTask
from .serializers import (
    VendorListSerializer, VendorDetailSerializer, VendorCreateUpdateSerializer,
    VendorCategorySerializer, VendorContactSerializer, VendorServiceSerializer,
    VendorNoteSerializer, VendorSummarySerializer, BulkVendorCreateSerializer,
    VendorTaskListSerializer, VendorTaskDetailSerializer, VendorTaskCreateUpdateSerializer,
    VendorTaskStatusUpdateSerializer, VendorTaskBulkActionSerializer, VendorTaskSummarySerializer,
    VendorTaskReminderSerializer
)
from .filters import VendorFilter, VendorContactFilter, VendorServiceFilter, VendorTaskFilter


@extend_schema_view(
    list=extend_schema(
        summary="List vendors",
        description="Retrieve a paginated list of vendors with filtering, search, and ordering capabilities.",
        parameters=[
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by vendor status (active, inactive, under_review, etc.)'
            ),
            OpenApiParameter(
                name='risk_level',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by risk level (low, medium, high, critical)'
            ),
            OpenApiParameter(
                name='category',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by vendor category ID'
            ),
            OpenApiParameter(
                name='assigned_to',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by assigned user ID'
            ),
            OpenApiParameter(
                name='contract_expiring_soon',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter vendors with contracts expiring within renewal notice period'
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search in vendor name, legal name, vendor ID, and business description'
            ),
        ],
        tags=['Vendors'],
    ),
    create=extend_schema(
        summary="Create vendor",
        description="Create a new vendor profile with comprehensive vendor information.",
        tags=['Vendors'],
    ),
    retrieve=extend_schema(
        summary="Get vendor details",
        description="Retrieve detailed information about a specific vendor including contacts and services.",
        tags=['Vendors'],
    ),
    update=extend_schema(
        summary="Update vendor",
        description="Update an existing vendor profile with new information.",
        tags=['Vendors'],
    ),
    destroy=extend_schema(
        summary="Delete vendor",
        description="Delete a vendor profile and all associated data.",
        tags=['Vendors'],
    ),
)
class VendorViewSet(viewsets.ModelViewSet):
    """
    **Vendor Profile Management**
    
    This ViewSet provides comprehensive vendor management including:
    - Complete vendor profile CRUD operations
    - Advanced filtering and search capabilities
    - Contract expiration tracking and alerts
    - Risk assessment and performance monitoring
    - Bulk vendor creation and management
    - Integration with contact and service management
    
    **Key Features:**
    - Multi-tenant data isolation and security
    - Automatic vendor ID generation (VEN-YYYY-NNNN)
    - Contract expiration alerts and renewal tracking
    - Risk level assessment and monitoring
    - Performance score tracking
    - Comprehensive audit trail
    
    **Vendor Management Workflow:**
    1. Create vendor profile with basic information
    2. Add contacts and services via related endpoints
    3. Complete risk assessment and compliance checks
    4. Monitor contract renewals and performance
    5. Maintain ongoing vendor relationship
    
    **Common Use Cases:**
    - Vendor onboarding and profile creation
    - Contract renewal management and alerts
    - Risk assessment and compliance tracking
    - Performance monitoring and evaluation
    - Vendor relationship management
    """
    
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = VendorFilter
    search_fields = ['name', 'legal_name', 'vendor_id', 'business_description']
    ordering_fields = [
        'name', 'vendor_id', 'status', 'risk_level', 'risk_score', 
        'performance_score', 'annual_spend', 'contract_end_date', 
        'created_at', 'updated_at'
    ]
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get vendors with tenant isolation and optimized queries."""
        return Vendor.objects.select_related(
            'category', 'assigned_to', 'created_by'
        ).prefetch_related('contacts', 'services')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return VendorListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return VendorCreateUpdateSerializer
        elif self.action == 'bulk_create':
            return BulkVendorCreateSerializer
        return VendorDetailSerializer
    
    def perform_create(self, serializer):
        """Set the creator when creating a vendor."""
        serializer.save(created_by=self.request.user)
    
    @extend_schema(
        summary="Update vendor status",
        description="Update vendor status with optional status change note.",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'enum': ['active', 'inactive', 'under_review', 'approved', 'suspended', 'terminated']},
                    'note': {'type': 'string', 'description': 'Optional note about the status change'}
                },
                'required': ['status']
            }
        },
        responses={200: VendorDetailSerializer},
        tags=['Vendors']
    )
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update vendor status with automatic logging."""
        vendor = self.get_object()
        old_status = vendor.status
        new_status = request.data.get('status')
        note_content = request.data.get('note', '')
        
        if not new_status:
            return Response(
                {'error': 'Status is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_status not in dict(Vendor.STATUS_CHOICES):
            return Response(
                {'error': 'Invalid status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        vendor.status = new_status
        vendor.save()
        
        # Create status change note
        note_title = f"Status changed from {old_status} to {new_status}"
        if note_content:
            note_title += f": {note_content}"
        
        VendorNote.objects.create(
            vendor=vendor,
            note_type='general',
            title=note_title,
            content=f"Vendor status updated from '{old_status}' to '{new_status}' by {request.user.get_full_name() or request.user.username}.\n\n{note_content}",
            created_by=request.user,
            is_internal=True
        )
        
        serializer = VendorDetailSerializer(vendor, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(
        summary="Add vendor note",
        description="Add a note or comment about the vendor.",
        request=VendorNoteSerializer,
        responses={201: VendorNoteSerializer},
        tags=['Vendors']
    )
    @action(detail=True, methods=['post'])
    def add_note(self, request, pk=None):
        """Add a note to a vendor."""
        vendor = self.get_object()
        serializer = VendorNoteSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            serializer.save(vendor=vendor, created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Bulk create vendors",
        description="Create multiple vendors in a single request with validation and error handling.",
        request=BulkVendorCreateSerializer,
        responses={201: {'type': 'object', 'properties': {'created_vendors': {'type': 'array'}}}},
        tags=['Vendors']
    )
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Create multiple vendors in bulk."""
        serializer = BulkVendorCreateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            vendors = serializer.save()
            response_serializer = VendorListSerializer(vendors, many=True, context={'request': request})
            return Response({
                'created_vendors': response_serializer.data,
                'count': len(vendors)
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Get vendor summary statistics",
        description="Retrieve comprehensive statistics about vendors including counts, risk distribution, and financial metrics.",
        responses={200: VendorSummarySerializer},
        tags=['Vendors']
    )
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get vendor summary statistics."""
        queryset = self.get_queryset()
        
        # Basic counts
        total_vendors = queryset.count()
        status_counts = queryset.values('status').annotate(count=Count('id'))
        status_dict = {item['status']: item['count'] for item in status_counts}
        
        # Risk distribution
        risk_counts = queryset.values('risk_level').annotate(count=Count('id'))
        risk_dict = {item['risk_level']: item['count'] for item in risk_counts}
        
        # Contract management
        today = timezone.now().date()
        contracts_expiring_soon = queryset.filter(
            contract_end_date__isnull=False,
            is_contract_expiring_soon=True
        ).count()
        expired_contracts = queryset.filter(
            contract_end_date__lt=today
        ).count()
        auto_renewal_contracts = queryset.filter(auto_renewal=True).count()
        
        # Categories
        category_counts = queryset.values('category__name').annotate(count=Count('id'))
        vendors_by_category = {
            item['category__name'] or 'Uncategorized': item['count'] 
            for item in category_counts
        }
        
        # Financial metrics
        financial_stats = queryset.aggregate(
            total_annual_spend=Sum('annual_spend'),
            average_performance_score=Avg('performance_score')
        )
        
        # Compliance
        vendors_with_dpa = queryset.filter(data_processing_agreement=True).count()
        vendors_with_security_assessment = queryset.filter(security_assessment_completed=True).count()
        
        # Services
        total_services = VendorService.objects.filter(vendor__in=queryset).count()
        active_services = VendorService.objects.filter(vendor__in=queryset, is_active=True).count()
        
        summary_data = {
            'total_vendors': total_vendors,
            'active_vendors': status_dict.get('active', 0),
            'inactive_vendors': status_dict.get('inactive', 0),
            'under_review_vendors': status_dict.get('under_review', 0),
            'critical_risk_vendors': risk_dict.get('critical', 0),
            'high_risk_vendors': risk_dict.get('high', 0),
            'medium_risk_vendors': risk_dict.get('medium', 0),
            'low_risk_vendors': risk_dict.get('low', 0),
            'contracts_expiring_soon': contracts_expiring_soon,
            'expired_contracts': expired_contracts,
            'auto_renewal_contracts': auto_renewal_contracts,
            'vendors_by_category': vendors_by_category,
            'total_annual_spend': financial_stats['total_annual_spend'],
            'average_performance_score': financial_stats['average_performance_score'],
            'vendors_with_dpa': vendors_with_dpa,
            'vendors_with_security_assessment': vendors_with_security_assessment,
            'total_services': total_services,
            'active_services': active_services,
        }
        
        serializer = VendorSummarySerializer(summary_data)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Get vendors by category",
        description="Retrieve vendors grouped by category with optional filtering.",
        parameters=[
            OpenApiParameter(
                name='include_counts',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Include vendor counts per category'
            ),
        ],
        tags=['Vendors']
    )
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get vendors grouped by category."""
        queryset = self.get_queryset()
        include_counts = request.query_params.get('include_counts', 'false').lower() == 'true'
        
        # Group vendors by category
        categories = VendorCategory.objects.prefetch_related('vendor_set').all()
        uncategorized_vendors = queryset.filter(category__isnull=True)
        
        result = {}
        
        for category in categories:
            category_vendors = queryset.filter(category=category)
            if include_counts:
                result[category.name] = {
                    'category_info': VendorCategorySerializer(category).data,
                    'vendors': VendorListSerializer(category_vendors, many=True, context={'request': request}).data,
                    'count': category_vendors.count()
                }
            else:
                result[category.name] = VendorListSerializer(category_vendors, many=True, context={'request': request}).data
        
        # Add uncategorized vendors
        if uncategorized_vendors.exists():
            if include_counts:
                result['Uncategorized'] = {
                    'category_info': None,
                    'vendors': VendorListSerializer(uncategorized_vendors, many=True, context={'request': request}).data,
                    'count': uncategorized_vendors.count()
                }
            else:
                result['Uncategorized'] = VendorListSerializer(uncategorized_vendors, many=True, context={'request': request}).data
        
        return Response(result)
    
    @extend_schema(
        summary="Get contract renewals",
        description="Get vendors with contracts expiring soon or already expired.",
        parameters=[
            OpenApiParameter(
                name='days_ahead',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Look ahead this many days for expiring contracts (default: 90)'
            ),
        ],
        tags=['Vendors']
    )
    @action(detail=False, methods=['get'])
    def contract_renewals(self, request):
        """Get vendors with upcoming contract renewals."""
        days_ahead = int(request.query_params.get('days_ahead', 90))
        today = timezone.now().date()
        future_date = today + timezone.timedelta(days=days_ahead)
        
        expiring_soon = self.get_queryset().filter(
            contract_end_date__isnull=False,
            contract_end_date__gte=today,
            contract_end_date__lte=future_date
        ).order_by('contract_end_date')
        
        expired = self.get_queryset().filter(
            contract_end_date__lt=today
        ).order_by('-contract_end_date')
        
        return Response({
            'expiring_soon': VendorListSerializer(expiring_soon, many=True, context={'request': request}).data,
            'expired': VendorListSerializer(expired, many=True, context={'request': request}).data,
            'expiring_count': expiring_soon.count(),
            'expired_count': expired.count()
        })


@extend_schema_view(tags=['Vendor Categories'])
class VendorCategoryViewSet(viewsets.ModelViewSet):
    """
    **Vendor Category Management**
    
    Manage vendor categories for classification and organization.
    Categories help organize vendors by business type, risk level, and compliance requirements.
    """
    
    queryset = VendorCategory.objects.all()
    serializer_class = VendorCategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


@extend_schema_view(tags=['Vendor Contacts'])
class VendorContactViewSet(viewsets.ModelViewSet):
    """
    **Vendor Contact Management**
    
    Manage contact persons for vendors with different roles and responsibilities.
    """
    
    serializer_class = VendorContactSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = VendorContactFilter
    search_fields = ['first_name', 'last_name', 'title', 'email']
    ordering_fields = ['first_name', 'last_name', 'contact_type', 'created_at']
    ordering = ['-is_primary', 'contact_type', 'first_name']
    
    def get_queryset(self):
        """Get contacts with vendor information."""
        return VendorContact.objects.select_related('vendor').all()


@extend_schema_view(tags=['Vendor Services'])
class VendorServiceViewSet(viewsets.ModelViewSet):
    """
    **Vendor Service Management**
    
    Manage services provided by vendors including categorization and risk assessment.
    """
    
    serializer_class = VendorServiceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = VendorServiceFilter
    search_fields = ['name', 'description', 'service_code']
    ordering_fields = ['name', 'category', 'cost_per_unit', 'created_at']
    ordering = ['vendor', 'name']
    
    def get_queryset(self):
        """Get services with vendor information."""
        return VendorService.objects.select_related('vendor').all()


@extend_schema_view(tags=['Vendor Notes'])
class VendorNoteViewSet(viewsets.ModelViewSet):
    """
    **Vendor Note Management**
    
    Manage notes and comments about vendors for tracking interactions and decisions.
    """
    
    serializer_class = VendorNoteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title', 'content']
    ordering_fields = ['note_type', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get notes with vendor and user information."""
        return VendorNote.objects.select_related('vendor', 'created_by').all()
    
    def perform_create(self, serializer):
        """Set the creator when creating a note."""
        serializer.save(created_by=self.request.user)


@extend_schema_view(tags=['Vendor Tasks'])
class VendorTaskViewSet(viewsets.ModelViewSet):
    """
    **Vendor Task Management**
    
    Comprehensive task management for vendor-related activities including contract renewals,
    security reviews, compliance assessments, and automated task generation.
    """
    
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = VendorTaskFilter
    search_fields = ['title', 'description', 'vendor__name', 'task_id']
    ordering_fields = [
        'due_date', 'priority', 'status', 'task_type', 'created_at', 'updated_at'
    ]
    ordering = ['due_date', '-priority']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return VendorTaskListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return VendorTaskCreateUpdateSerializer
        elif self.action == 'update_status':
            return VendorTaskStatusUpdateSerializer
        elif self.action == 'bulk_action':
            return VendorTaskBulkActionSerializer
        elif self.action == 'summary':
            return VendorTaskSummarySerializer
        elif self.action == 'send_reminders':
            return VendorTaskReminderSerializer
        else:
            return VendorTaskDetailSerializer
    
    def get_queryset(self):
        """Get tasks with related data optimized."""
        return VendorTask.objects.select_related(
            'vendor', 'assigned_to', 'created_by', 'service_reference'
        ).all()
    
    @extend_schema(
        summary="Get task summary statistics",
        description="Get comprehensive statistics about vendor tasks including status, priority, and due date analysis.",
        responses={200: VendorTaskSummarySerializer}
    )
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get comprehensive task summary statistics."""
        queryset = self.get_queryset()
        
        # Basic counts
        total_tasks = queryset.count()
        active_tasks = queryset.filter(status__in=['pending', 'in_progress']).count()
        completed_tasks = queryset.filter(status='completed').count()
        overdue_tasks = queryset.filter(
            due_date__lt=timezone.now().date(),
            status__in=['pending', 'in_progress']
        ).count()
        
        # Status breakdown
        status_counts = queryset.values('status').annotate(count=Count('id'))
        status_breakdown = {item['status']: item['count'] for item in status_counts}
        
        # Priority breakdown
        priority_counts = queryset.values('priority').annotate(count=Count('id'))
        priority_breakdown = {item['priority']: item['count'] for item in priority_counts}
        
        # Task type breakdown
        task_type_counts = queryset.values('task_type').annotate(count=Count('id'))
        task_type_breakdown = {item['task_type']: item['count'] for item in task_type_counts}
        
        # Due date analysis
        today = timezone.now().date()
        week_end = today + timezone.timedelta(days=7)
        month_end = today + timezone.timedelta(days=30)
        next_month_end = today + timezone.timedelta(days=60)
        
        due_this_week = queryset.filter(
            due_date__gte=today,
            due_date__lte=week_end,
            status__in=['pending', 'in_progress']
        ).count()
        
        due_this_month = queryset.filter(
            due_date__gte=today,
            due_date__lte=month_end,
            status__in=['pending', 'in_progress']
        ).count()
        
        due_next_month = queryset.filter(
            due_date__gt=month_end,
            due_date__lte=next_month_end,
            status__in=['pending', 'in_progress']
        ).count()
        
        # Assignment analysis
        assigned_tasks = queryset.filter(assigned_to__isnull=False).count()
        unassigned_tasks = queryset.filter(assigned_to__isnull=True).count()
        
        # Automation statistics
        auto_generated_tasks = queryset.filter(auto_generated=True).count()
        manual_tasks = queryset.filter(auto_generated=False).count()
        
        # Performance metrics
        completed_queryset = queryset.filter(status='completed', completed_date__isnull=False)
        
        # Calculate average completion time (in days)
        completion_times = []
        for task in completed_queryset:
            if task.created_at and task.completed_date:
                delta = task.completed_date.date() - task.created_at.date()
                completion_times.append(delta.days)
        
        average_completion_time = sum(completion_times) / len(completion_times) if completion_times else None
        
        # Calculate on-time completion rate
        on_time_completions = completed_queryset.filter(
            completed_date__date__lte=F('due_date')
        ).count()
        on_time_completion_rate = (
            (on_time_completions / completed_tasks * 100) if completed_tasks > 0 else None
        )
        
        summary_data = {
            'total_tasks': total_tasks,
            'active_tasks': active_tasks,
            'completed_tasks': completed_tasks,
            'overdue_tasks': overdue_tasks,
            'status_breakdown': status_breakdown,
            'priority_breakdown': priority_breakdown,
            'task_type_breakdown': task_type_breakdown,
            'due_this_week': due_this_week,
            'due_this_month': due_this_month,
            'due_next_month': due_next_month,
            'assigned_tasks': assigned_tasks,
            'unassigned_tasks': unassigned_tasks,
            'auto_generated_tasks': auto_generated_tasks,
            'manual_tasks': manual_tasks,
            'average_completion_time': average_completion_time,
            'on_time_completion_rate': on_time_completion_rate,
        }
        
        serializer = VendorTaskSummarySerializer(summary_data)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Update task status",
        description="Update the status of a specific task with optional completion notes.",
        request=VendorTaskStatusUpdateSerializer,
        responses={200: VendorTaskDetailSerializer}
    )
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update task status with validation and logging."""
        task = self.get_object()
        serializer = VendorTaskStatusUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            old_status = task.status
            new_status = serializer.validated_data['status']
            completion_notes = serializer.validated_data.get('completion_notes', '')
            
            task.status = new_status
            if completion_notes:
                task.completion_notes = completion_notes
            
            task.save()
            
            # Send completion notification if task was completed
            if new_status == 'completed' and old_status != 'completed':
                from .task_notifications import get_notification_service
                notification_service = get_notification_service()
                notification_service.send_task_completion_notification(task)
            
            response_serializer = VendorTaskDetailSerializer(task, context={'request': request})
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Bulk task actions",
        description="Perform bulk actions on multiple tasks (update status, assign users, etc.).",
        request=VendorTaskBulkActionSerializer,
        responses={200: OpenApiResponse(description="Bulk action completed")}
    )
    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """Perform bulk actions on selected tasks."""
        serializer = VendorTaskBulkActionSerializer(data=request.data)
        
        if serializer.is_valid():
            task_ids = serializer.validated_data['task_ids']
            action = serializer.validated_data['action']
            
            tasks = VendorTask.objects.filter(id__in=task_ids)
            updated_count = 0
            
            if action == 'update_status':
                new_status = serializer.validated_data['status']
                notes = serializer.validated_data.get('notes', '')
                
                for task in tasks:
                    task.status = new_status
                    if notes and not task.completion_notes:
                        task.completion_notes = notes
                    task.save()
                    updated_count += 1
                    
            elif action == 'assign_user':
                assigned_to = serializer.validated_data['assigned_to']
                tasks.update(assigned_to=assigned_to)
                updated_count = tasks.count()
                
            elif action == 'update_priority':
                new_priority = serializer.validated_data['priority']
                tasks.update(priority=new_priority)
                updated_count = tasks.count()
                
            elif action == 'send_reminders':
                from .task_notifications import get_notification_service
                notification_service = get_notification_service()
                results = notification_service.send_batch_reminders(list(tasks))
                updated_count = results.get('sent', 0)
            
            return Response({
                'status': 'success',
                'message': f'Bulk {action} completed',
                'updated_count': updated_count
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Send task reminders",
        description="Send reminder emails for tasks that are due soon or overdue.",
        request=VendorTaskReminderSerializer,
        responses={200: OpenApiResponse(description="Reminders sent")}
    )
    @action(detail=False, methods=['post'])
    def send_reminders(self, request):
        """Send reminder emails for specified tasks or all due tasks."""
        serializer = VendorTaskReminderSerializer(data=request.data)
        
        if serializer.is_valid():
            task_ids = serializer.validated_data.get('task_ids')
            force_send = serializer.validated_data.get('force_send', False)
            additional_recipients = serializer.validated_data.get('additional_recipients', [])
            
            # Get tasks to send reminders for
            if task_ids:
                tasks = VendorTask.objects.filter(id__in=task_ids)
            else:
                tasks = VendorTask.objects.filter(status__in=['pending', 'in_progress'])
            
            # Filter tasks that should receive reminders
            if not force_send:
                tasks = [task for task in tasks if task.should_send_reminder]
            
            # Send reminders
            from .task_notifications import get_notification_service
            notification_service = get_notification_service()
            
            results = {'sent': 0, 'failed': 0, 'skipped': 0}
            
            for task in tasks:
                # Add additional recipients to task temporarily
                original_recipients = task.reminder_recipients.copy()
                task.reminder_recipients.extend(additional_recipients)
                
                success = notification_service.send_task_reminder(task)
                if success:
                    results['sent'] += 1
                else:
                    results['failed'] += 1
                
                # Restore original recipients
                task.reminder_recipients = original_recipients
            
            return Response({
                'status': 'success',
                'message': f"Sent {results['sent']} reminders, {results['failed']} failed",
                'results': results
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Get upcoming tasks",
        description="Get tasks that are due within a specified number of days.",
        parameters=[
            OpenApiParameter(
                name='days',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Number of days to look ahead (default: 7)',
                default=7
            )
        ]
    )
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get tasks due within specified number of days."""
        days = int(request.query_params.get('days', 7))
        end_date = timezone.now().date() + timezone.timedelta(days=days)
        
        upcoming_tasks = self.get_queryset().filter(
            due_date__lte=end_date,
            due_date__gte=timezone.now().date(),
            status__in=['pending', 'in_progress']
        ).order_by('due_date', '-priority')
        
        serializer = VendorTaskListSerializer(upcoming_tasks, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(
        summary="Get overdue tasks",
        description="Get all tasks that are past their due date."
    )
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get all overdue tasks."""
        overdue_tasks = self.get_queryset().filter(
            due_date__lt=timezone.now().date(),
            status__in=['pending', 'in_progress']
        ).order_by('due_date')
        
        serializer = VendorTaskListSerializer(overdue_tasks, many=True, context={'request': request})
        return Response(serializer.data)
    
    @extend_schema(
        summary="Generate automatic tasks",
        description="Trigger automatic task generation based on contract dates and vendor requirements.",
        responses={200: OpenApiResponse(description="Automatic tasks generated")}
    )
    @action(detail=False, methods=['post'])
    def generate_tasks(self, request):
        """Trigger automatic task generation."""
        from .task_automation import get_automation_service
        
        automation_service = get_automation_service()
        results = automation_service.run_daily_automation()
        
        total_created = sum(results.values())
        
        return Response({
            'status': 'success',
            'message': f'Generated {total_created} automatic tasks',
            'breakdown': results
        })
    
    def perform_create(self, serializer):
        """Set creator when creating a task."""
        serializer.save(created_by=self.request.user)