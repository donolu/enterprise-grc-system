from rest_framework import viewsets, status, filters, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q, Case, When, Value, IntegerField
from django.utils import timezone
from datetime import datetime, timedelta

from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from .models import (
    Risk, RiskCategory, RiskMatrix, RiskNote,
    RiskAction, RiskActionNote, RiskActionEvidence,
    RiskActionReminderConfiguration
)
from .serializers import (
    RiskListSerializer, RiskDetailSerializer, RiskCreateUpdateSerializer,
    RiskStatusUpdateSerializer, BulkRiskCreateSerializer, RiskSummarySerializer,
    RiskCategorySerializer, RiskMatrixSerializer, RiskNoteSerializer,
    RiskActionListSerializer, RiskActionDetailSerializer, RiskActionCreateUpdateSerializer,
    RiskActionStatusUpdateSerializer, RiskActionNoteCreateSerializer, RiskActionNoteSerializer,
    RiskActionEvidenceCreateUpdateSerializer, RiskActionEvidenceSerializer, RiskActionBulkCreateSerializer,
    RiskActionSummarySerializer, RiskActionReminderConfigurationSerializer
)
from .filters import RiskFilter, RiskActionFilter
from .analytics import RiskAnalyticsService, RiskReportGenerator


@extend_schema_view(
    list=extend_schema(
        summary="List risks",
        description="Retrieve a paginated list of risks with comprehensive filtering, searching, and ordering capabilities.",
        parameters=[
            OpenApiParameter(
                name='risk_level',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by risk level (low, medium, high, critical)'
            ),
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by risk status'
            ),
            OpenApiParameter(
                name='category',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by category ID'
            ),
            OpenApiParameter(
                name='risk_owner',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by risk owner user ID'
            ),
            OpenApiParameter(
                name='overdue_review',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Show only risks overdue for review'
            ),
            OpenApiParameter(
                name='active_only',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Show only active risks (excludes closed/transferred)'
            ),
            OpenApiParameter(
                name='my_risks',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Show only risks owned by current user'
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search across risk_id, title, description'
            ),
            OpenApiParameter(
                name='ordering',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Order by: risk_level, risk_score, title, identified_date, next_review_date (prefix with - for descending)'
            ),
        ],
        tags=['Risk Management'],
        examples=[
            OpenApiExample(
                'High priority risks',
                summary='Get high and critical risks',
                description='Example of filtering for high priority risks',
                value='?risk_level=high,critical&active_only=true'
            ),
        ]
    ),
    create=extend_schema(
        summary="Create new risk",
        description="Create a new risk entry with impact and likelihood assessment.",
        tags=['Risk Management'],
    ),
    retrieve=extend_schema(
        summary="Get risk details",
        description="Retrieve detailed information about a specific risk including notes and history.",
        tags=['Risk Management'],
    ),
    update=extend_schema(
        summary="Update risk",
        description="Update an existing risk entry. Risk level will be automatically recalculated.",
        tags=['Risk Management'],
    ),
    partial_update=extend_schema(
        summary="Partially update risk",
        description="Update specific fields of an existing risk entry.",
        tags=['Risk Management'],
    ),
    destroy=extend_schema(
        summary="Delete risk",
        description="Delete a risk entry and all associated notes.",
        tags=['Risk Management'],
    ),
)
class RiskViewSet(viewsets.ModelViewSet):
    """
    **Risk Management**
    
    This ViewSet provides comprehensive risk management capabilities including:
    - Full risk lifecycle management (identification, assessment, treatment, closure)
    - Risk assessment with configurable impact and likelihood ratings
    - Automated risk level calculation using risk matrices
    - Risk categorization and ownership management
    - Advanced filtering and search capabilities
    
    **Key Features:**
    - Configurable risk matrices for different assessment approaches
    - Risk treatment strategy tracking (mitigate, accept, transfer, avoid)
    - Review date management with overdue notifications
    - Risk notes and comment system for tracking progress
    - Bulk risk creation for efficiency
    
    **Risk Assessment Workflow:**
    1. Identify and create risk
    2. Assess impact and likelihood
    3. Calculate risk level (automatic)
    4. Plan and implement treatment
    5. Monitor and review regularly
    
    **Common Use Cases:**
    - Maintain organizational risk register
    - Track risk treatment progress
    - Generate risk reports and analytics
    - Monitor risk review schedules
    """
    
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = RiskFilter
    search_fields = ['risk_id', 'title', 'description']
    ordering_fields = [
        'risk_level', 'risk_score', 'title', 'status',
        'identified_date', 'last_assessed_date', 'next_review_date',
        'created_at', 'updated_at'
    ]
    ordering = ['-risk_level', '-risk_score', 'title']
    
    def get_queryset(self):
        """Return risks for the current tenant with optimized queries."""
        queryset = Risk.objects.select_related(
            'category', 'risk_owner', 'risk_matrix', 'created_by'
        ).prefetch_related('notes')
        
        # Apply common filters
        if self.request.query_params.get('overdue_review'):
            queryset = queryset.filter(
                next_review_date__lt=timezone.now().date()
            ).exclude(
                next_review_date__isnull=True
            )
        
        if self.request.query_params.get('active_only'):
            queryset = queryset.filter(status__in=[
                'identified', 'assessed', 'treatment_planned', 
                'treatment_in_progress', 'mitigated', 'accepted'
            ])
        
        if self.request.query_params.get('my_risks'):
            queryset = queryset.filter(risk_owner=self.request.user)
        
        return queryset
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return RiskListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return RiskCreateUpdateSerializer
        else:
            return RiskDetailSerializer
    
    def perform_create(self, serializer):
        """Create risk with current user as creator."""
        serializer.save(created_by=self.request.user)
    
    @extend_schema(
        summary="Update risk status",
        description="Update risk status with optional treatment strategy and notes. Automatically creates a status change note.",
        request=RiskStatusUpdateSerializer,
        responses={
            200: RiskDetailSerializer,
            400: OpenApiResponse(description='Invalid status update data'),
            404: OpenApiResponse(description='Risk not found'),
        },
        tags=['Risk Management'],
    )
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update risk status with notes and automatic logging."""
        risk = self.get_object()
        serializer = RiskStatusUpdateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            updated_risk = serializer.update_risk_status(risk)
            response_serializer = RiskDetailSerializer(updated_risk)
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Add risk note",
        description="Add a note or comment to a risk for tracking progress and decisions.",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'note': {'type': 'string', 'description': 'Note content'},
                    'note_type': {
                        'type': 'string',
                        'enum': ['general', 'assessment', 'treatment', 'review', 'status_change'],
                        'description': 'Type of note'
                    }
                },
                'required': ['note']
            }
        },
        responses={
            201: RiskNoteSerializer,
            400: OpenApiResponse(description='Invalid note data'),
        },
        tags=['Risk Management'],
    )
    @action(detail=True, methods=['post'])
    def add_note(self, request, pk=None):
        """Add a note to a risk."""
        risk = self.get_object()
        
        note_data = request.data.copy()
        note_data['risk'] = risk.id
        
        serializer = RiskNoteSerializer(data=note_data)
        if serializer.is_valid():
            serializer.save(risk=risk, created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Bulk create risks",
        description="Create multiple risks in a single operation with common defaults and individual overrides.",
        request=BulkRiskCreateSerializer,
        responses={
            201: OpenApiResponse(
                description='Risks created successfully',
                examples=[
                    OpenApiExample(
                        'Bulk Creation Success',
                        summary='Successful bulk risk creation',
                        value={
                            'message': 'Created 5 risks successfully',
                            'created_count': 5,
                            'error_count': 0,
                            'risks': [
                                {
                                    'id': 1,
                                    'risk_id': 'RISK-2024-0001',
                                    'title': 'Data Breach Risk',
                                    'risk_level': 'high'
                                }
                            ],
                            'errors': []
                        }
                    ),
                ]
            ),
            400: OpenApiResponse(description='Invalid bulk creation data'),
        },
        tags=['Risk Management'],
    )
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Create multiple risks in bulk."""
        serializer = BulkRiskCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            created_risks, errors = serializer.create_bulk_risks()
            
            # Serialize created risks
            risk_serializer = RiskListSerializer(created_risks, many=True)
            
            return Response({
                'message': f'Created {len(created_risks)} risks successfully',
                'created_count': len(created_risks),
                'error_count': len(errors),
                'risks': risk_serializer.data,
                'errors': errors
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Get risk summary and analytics",
        description="Generate comprehensive risk summary with statistics, breakdowns, and priority lists.",
        responses={
            200: RiskSummarySerializer,
        },
        tags=['Risk Management'],
    )
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get risk summary and analytics."""
        queryset = self.get_queryset()
        
        # Basic counts
        total_risks = queryset.count()
        active_risks = queryset.filter(status__in=[
            'identified', 'assessed', 'treatment_planned',
            'treatment_in_progress', 'mitigated', 'accepted'
        ]).count()
        overdue_reviews = queryset.filter(
            next_review_date__lt=timezone.now().date()
        ).exclude(next_review_date__isnull=True).count()
        
        # Risk level breakdown
        by_risk_level = dict(queryset.values('risk_level').annotate(
            count=Count('id')
        ).values_list('risk_level', 'count'))
        
        # Status breakdown
        by_status = dict(queryset.values('status').annotate(
            count=Count('id')
        ).values_list('status', 'count'))
        
        # Category breakdown
        by_category = dict(queryset.select_related('category').values(
            'category__name'
        ).annotate(
            count=Count('id')
        ).values_list('category__name', 'count'))
        
        # Treatment strategy breakdown
        by_treatment_strategy = dict(queryset.exclude(
            treatment_strategy__isnull=True
        ).exclude(
            treatment_strategy=''
        ).values('treatment_strategy').annotate(
            count=Count('id')
        ).values_list('treatment_strategy', 'count'))
        
        # Recent risks (last 30 days)
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        recent_risks = queryset.filter(
            created_at__date__gte=thirty_days_ago
        ).order_by('-created_at')[:10]
        
        # High priority risks
        high_priority_risks = queryset.filter(
            risk_level__in=['high', 'critical']
        ).filter(status__in=[
            'identified', 'assessed', 'treatment_planned', 'treatment_in_progress'
        ]).order_by('-risk_score', 'title')[:10]
        
        # Overdue review risks
        overdue_review_risks = queryset.filter(
            next_review_date__lt=timezone.now().date()
        ).exclude(
            next_review_date__isnull=True
        ).order_by('next_review_date')[:10]
        
        # Serialize lists
        recent_serializer = RiskListSerializer(recent_risks, many=True)
        high_priority_serializer = RiskListSerializer(high_priority_risks, many=True)
        overdue_serializer = RiskListSerializer(overdue_review_risks, many=True)
        
        summary_data = {
            'total_risks': total_risks,
            'active_risks': active_risks,
            'overdue_reviews': overdue_reviews,
            'by_risk_level': by_risk_level,
            'by_status': by_status,
            'by_category': by_category,
            'by_treatment_strategy': by_treatment_strategy,
            'recent_risks': recent_serializer.data,
            'high_priority_risks': high_priority_serializer.data,
            'overdue_review_risks': overdue_serializer.data,
        }
        
        return Response(summary_data)
    
    @extend_schema(
        summary="Get risks by category",
        description="Retrieve risks grouped by category with counts and summaries.",
        responses={
            200: OpenApiResponse(
                description='Risks grouped by category',
                examples=[
                    OpenApiExample(
                        'Category Breakdown',
                        summary='Risks grouped by category',
                        value={
                            'categories': [
                                {
                                    'category': 'Cybersecurity',
                                    'count': 15,
                                    'high_priority_count': 3,
                                    'risks': []
                                }
                            ]
                        }
                    ),
                ]
            ),
        },
        tags=['Risk Management'],
    )
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get risks grouped by category."""
        queryset = self.get_queryset()
        
        categories = RiskCategory.objects.annotate(
            risk_count=Count('risks', filter=Q(risks__in=queryset)),
            high_priority_count=Count(
                'risks',
                filter=Q(
                    risks__in=queryset,
                    risks__risk_level__in=['high', 'critical']
                )
            )
        ).filter(risk_count__gt=0).order_by('name')
        
        category_data = []
        for category in categories:
            category_risks = queryset.filter(category=category)
            risk_serializer = RiskListSerializer(category_risks, many=True)
            
            category_data.append({
                'category': category.name,
                'category_id': category.id,
                'count': category.risk_count,
                'high_priority_count': category.high_priority_count,
                'risks': risk_serializer.data
            })
        
        # Include uncategorized risks
        uncategorized_risks = queryset.filter(category__isnull=True)
        if uncategorized_risks.exists():
            risk_serializer = RiskListSerializer(uncategorized_risks, many=True)
            category_data.append({
                'category': 'Uncategorized',
                'category_id': None,
                'count': uncategorized_risks.count(),
                'high_priority_count': uncategorized_risks.filter(
                    risk_level__in=['high', 'critical']
                ).count(),
                'risks': risk_serializer.data
            })
        
        return Response({'categories': category_data})


@extend_schema_view(
    list=extend_schema(
        summary="List risk categories",
        description="Retrieve all risk categories with risk counts.",
        tags=['Risk Management'],
    ),
    create=extend_schema(
        summary="Create risk category",
        description="Create a new risk category for organizing risks.",
        tags=['Risk Management'],
    ),
    retrieve=extend_schema(
        summary="Get category details",
        description="Retrieve detailed information about a risk category.",
        tags=['Risk Management'],
    ),
    update=extend_schema(
        summary="Update risk category",
        description="Update an existing risk category.",
        tags=['Risk Management'],
    ),
    destroy=extend_schema(
        summary="Delete risk category",
        description="Delete a risk category. Risks in this category will become uncategorized.",
        tags=['Risk Management'],
    ),
)
class RiskCategoryViewSet(viewsets.ModelViewSet):
    """
    **Risk Category Management**
    
    Manage risk categories for organizing and classifying risks.
    Categories help in grouping related risks and generating targeted reports.
    """
    
    queryset = RiskCategory.objects.all()
    serializer_class = RiskCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering = ['name']


@extend_schema_view(
    list=extend_schema(
        summary="List risk matrices",
        description="Retrieve all available risk assessment matrices.",
        tags=['Risk Management'],
    ),
    create=extend_schema(
        summary="Create risk matrix",
        description="Create a new risk assessment matrix with custom configuration.",
        tags=['Risk Management'],
    ),
    retrieve=extend_schema(
        summary="Get matrix details",
        description="Retrieve detailed information about a risk matrix including configuration.",
        tags=['Risk Management'],
    ),
    update=extend_schema(
        summary="Update risk matrix",
        description="Update an existing risk matrix configuration.",
        tags=['Risk Management'],
    ),
    destroy=extend_schema(
        summary="Delete risk matrix",
        description="Delete a risk matrix. Cannot delete if it's the default matrix or in use by risks.",
        tags=['Risk Management'],
    ),
)
class RiskMatrixViewSet(viewsets.ModelViewSet):
    """
    **Risk Matrix Management**
    
    Manage configurable risk assessment matrices for calculating risk levels
    based on impact and likelihood combinations.
    """
    
    queryset = RiskMatrix.objects.all()
    serializer_class = RiskMatrixSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering = ['-is_default', 'name']
    
    def perform_create(self, serializer):
        """Create matrix with current user as creator."""
        serializer.save(created_by=self.request.user)


@extend_schema_view(
    list=extend_schema(
        summary="List risk actions",
        description="Retrieve a paginated list of risk actions with comprehensive filtering, searching, and ordering capabilities.",
        parameters=[
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by action status (pending, in_progress, completed, cancelled, deferred)'
            ),
            OpenApiParameter(
                name='priority',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by action priority (low, medium, high, critical)'
            ),
            OpenApiParameter(
                name='assigned_to',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by assigned user ID'
            ),
            OpenApiParameter(
                name='overdue',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Show only overdue actions'
            ),
            OpenApiParameter(
                name='due_soon',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Show only actions due within 7 days'
            ),
            OpenApiParameter(
                name='assigned_to_me',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Show only actions assigned to current user'
            ),
            OpenApiParameter(
                name='active_only',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Show only active actions (excludes completed/cancelled)'
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search across action_id, title, description, risk details'
            ),
            OpenApiParameter(
                name='ordering',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Order by: due_date, priority, status, title, progress_percentage (prefix with - for descending)'
            ),
        ],
        tags=['Risk Actions'],
    ),
    create=extend_schema(
        summary="Create new risk action",
        description="Create a new risk action with assignment and scheduling.",
        tags=['Risk Actions'],
    ),
    retrieve=extend_schema(
        summary="Get risk action details",
        description="Retrieve detailed information about a specific risk action including notes and evidence.",
        tags=['Risk Actions'],
    ),
    update=extend_schema(
        summary="Update risk action",
        description="Update an existing risk action. Progress and status will be validated.",
        tags=['Risk Actions'],
    ),
    partial_update=extend_schema(
        summary="Partially update risk action",
        description="Update specific fields of an existing risk action.",
        tags=['Risk Actions'],
    ),
    destroy=extend_schema(
        summary="Delete risk action",
        description="Delete a risk action and all associated notes and evidence.",
        tags=['Risk Actions'],
    ),
)
class RiskActionViewSet(viewsets.ModelViewSet):
    """
    **Risk Action Management**
    
    This ViewSet provides comprehensive risk action management capabilities including:
    - Risk treatment action lifecycle management (creation, assignment, tracking, completion)
    - Progress tracking with percentage completion and status updates
    - Evidence management for action completion documentation
    - Automated notification system for assignments and status changes
    - Advanced filtering and search capabilities
    
    **Key Features:**
    - Action assignment and ownership management
    - Progress tracking with notes and status updates
    - Evidence upload and validation system
    - Automated reminder notifications for due dates
    - Bulk action creation for efficiency
    
    **Action Workflow:**
    1. Create action linked to a risk
    2. Assign to responsible user
    3. Track progress with percentage and notes
    4. Upload evidence as tasks are completed
    5. Mark as completed when requirements are met
    
    **Common Use Cases:**
    - Implement risk treatment strategies
    - Track remediation progress
    - Manage evidence collection
    - Monitor action due dates and assignments
    """
    
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = RiskActionFilter
    search_fields = ['action_id', 'title', 'description', 'risk__risk_id', 'risk__title']
    ordering_fields = [
        'due_date', 'priority', 'status', 'title', 'progress_percentage',
        'start_date', 'completed_date', 'created_at', 'updated_at'
    ]
    ordering = ['due_date', '-priority', 'title']
    
    def get_queryset(self):
        """Return risk actions for the current tenant with optimized queries."""
        queryset = RiskAction.objects.select_related(
            'risk', 'risk__category', 'assigned_to', 'created_by'
        ).prefetch_related('notes', 'evidence')
        
        # Apply common filters
        if self.request.query_params.get('overdue'):
            queryset = queryset.filter(
                due_date__lt=timezone.now().date(),
                status__in=['pending', 'in_progress', 'deferred']
            )
        
        if self.request.query_params.get('due_soon'):
            today = timezone.now().date()
            week_from_now = today + timedelta(days=7)
            queryset = queryset.filter(
                due_date__gte=today,
                due_date__lte=week_from_now,
                status__in=['pending', 'in_progress', 'deferred']
            )
        
        if self.request.query_params.get('active_only'):
            queryset = queryset.filter(status__in=['pending', 'in_progress', 'deferred'])
        
        if self.request.query_params.get('assigned_to_me'):
            queryset = queryset.filter(assigned_to=self.request.user)
        
        return queryset
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return RiskActionListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return RiskActionCreateUpdateSerializer
        else:
            return RiskActionDetailSerializer
    
    def perform_create(self, serializer):
        """Create risk action with current user as creator and send notifications."""
        from .notifications import RiskActionReminderService
        
        action = serializer.save(created_by=self.request.user)
        
        # Send assignment notification if user is assigned
        if action.assigned_to and action.assigned_to != self.request.user:
            RiskActionReminderService.send_assignment_notification(
                action, action.assigned_to, self.request.user
            )
    
    @extend_schema(
        summary="Update risk action status",
        description="Update the status of a risk action with optional progress percentage and note.",
        request=RiskActionStatusUpdateSerializer,
        responses={
            200: RiskActionDetailSerializer,
            400: OpenApiResponse(description='Invalid status update data'),
            404: OpenApiResponse(description='Risk action not found'),
        },
        tags=['Risk Actions'],
        examples=[
            OpenApiExample(
                'Complete Action',
                summary='Mark action as completed',
                description='Example of completing a risk action with note',
                value={
                    'status': 'completed',
                    'progress_percentage': 100,
                    'note': 'All required tasks completed and evidence uploaded.'
                }
            ),
        ]
    )
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update risk action status with automatic progress and note handling."""
        action = self.get_object()
        serializer = RiskActionStatusUpdateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            updated_action = serializer.update_action_status(action)
            response_serializer = RiskActionDetailSerializer(
                updated_action,
                context={'request': request}
            )
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Add progress note",
        description="Add a progress note to track work done on this risk action.",
        request=RiskActionNoteCreateSerializer,
        responses={
            201: RiskActionNoteSerializer,
            400: OpenApiResponse(description='Invalid note data'),
            404: OpenApiResponse(description='Risk action not found'),
        },
        tags=['Risk Actions'],
    )
    @action(detail=True, methods=['post'])
    def add_note(self, request, pk=None):
        """Add a progress note to the risk action."""
        action = self.get_object()
        serializer = RiskActionNoteCreateSerializer(
            data=request.data,
            context={'request': request, 'action': action}
        )
        
        if serializer.is_valid():
            note = serializer.save()
            response_serializer = RiskActionNoteSerializer(
                note,
                context={'request': request}
            )
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Upload evidence",
        description="Upload evidence file or link to document action completion.",
        request=RiskActionEvidenceCreateUpdateSerializer,
        responses={
            201: RiskActionEvidenceSerializer,
            400: OpenApiResponse(description='Invalid evidence data'),
            404: OpenApiResponse(description='Risk action not found'),
        },
        tags=['Risk Actions'],
    )
    @action(detail=True, methods=['post'])
    def upload_evidence(self, request, pk=None):
        """Upload evidence for the risk action."""
        action = self.get_object()
        serializer = RiskActionEvidenceCreateUpdateSerializer(
            data=request.data,
            context={'request': request, 'action': action}
        )
        
        if serializer.is_valid():
            evidence = serializer.save()
            response_serializer = RiskActionEvidenceSerializer(
                evidence,
                context={'request': request}
            )
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Bulk create risk actions",
        description="Create multiple risk actions in a single operation for efficiency.",
        request=RiskActionBulkCreateSerializer,
        responses={
            201: OpenApiResponse(
                description='Actions created successfully',
                examples=[
                    OpenApiExample(
                        'Bulk Creation Results',
                        summary='Successful bulk creation with results',
                        value={
                            'created_count': 8,
                            'error_count': 2,
                            'created_actions': [],
                            'errors': []
                        }
                    ),
                ]
            ),
            400: OpenApiResponse(description='Invalid bulk creation data'),
        },
        tags=['Risk Actions'],
    )
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Create multiple risk actions in bulk."""
        serializer = RiskActionBulkCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            created_actions, errors = serializer.create_bulk_actions()
            
            # Serialize created actions for response
            created_serializer = RiskActionListSerializer(
                created_actions, 
                many=True, 
                context={'request': request}
            )
            
            return Response({
                'created_count': len(created_actions),
                'error_count': len(errors),
                'created_actions': created_serializer.data,
                'errors': errors
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Get risk action summary",
        description="Retrieve comprehensive statistics and analytics for risk actions.",
        responses={
            200: RiskActionSummarySerializer,
        },
        tags=['Risk Actions'],
    )
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get comprehensive risk action statistics."""
        queryset = self.get_queryset()
        
        # Basic counts
        total_actions = queryset.count()
        
        # Status breakdown
        by_status = {}
        for choice_value, choice_label in RiskAction.STATUS_CHOICES:
            count = queryset.filter(status=choice_value).count()
            by_status[choice_value] = {'count': count, 'label': choice_label}
        
        # Priority breakdown
        by_priority = {}
        for choice_value, choice_label in RiskAction.PRIORITY_CHOICES:
            count = queryset.filter(priority=choice_value).count()
            by_priority[choice_value] = {'count': count, 'label': choice_label}
        
        # Time-based metrics
        today = timezone.now().date()
        overdue_count = queryset.filter(
            due_date__lt=today,
            status__in=['pending', 'in_progress', 'deferred']
        ).count()
        
        due_this_week = queryset.filter(
            due_date__gte=today,
            due_date__lte=today + timedelta(days=7),
            status__in=['pending', 'in_progress', 'deferred']
        ).count()
        
        high_priority_pending = queryset.filter(
            priority__in=['high', 'critical'],
            status__in=['pending', 'in_progress', 'deferred']
        ).count()
        
        # Completion rate
        completed_count = queryset.filter(status='completed').count()
        completion_rate = (completed_count / total_actions * 100) if total_actions > 0 else 0
        
        # Sample actions for different categories
        overdue_actions = queryset.filter(
            due_date__lt=today,
            status__in=['pending', 'in_progress', 'deferred']
        ).order_by('due_date')[:5]
        
        due_soon_actions = queryset.filter(
            due_date__gte=today,
            due_date__lte=today + timedelta(days=7),
            status__in=['pending', 'in_progress', 'deferred']
        ).order_by('due_date')[:5]
        
        high_priority_actions = queryset.filter(
            priority__in=['high', 'critical'],
            status__in=['pending', 'in_progress', 'deferred']
        ).order_by('due_date')[:5]
        
        # Serialize sample actions
        overdue_serializer = RiskActionListSerializer(overdue_actions, many=True, context={'request': request})
        due_soon_serializer = RiskActionListSerializer(due_soon_actions, many=True, context={'request': request})
        high_priority_serializer = RiskActionListSerializer(high_priority_actions, many=True, context={'request': request})
        
        summary_data = {
            'total_actions': total_actions,
            'by_status': by_status,
            'by_priority': by_priority,
            'overdue_count': overdue_count,
            'due_this_week': due_this_week,
            'high_priority_pending': high_priority_pending,
            'completion_rate': round(completion_rate, 2),
            'overdue_actions': overdue_serializer.data,
            'due_soon_actions': due_soon_serializer.data,
            'high_priority_actions': high_priority_serializer.data,
        }
        
        return Response(summary_data)
    
    @extend_schema(
        summary="Get actions by risk",
        description="Retrieve risk actions grouped by risk with counts and summaries.",
        responses={
            200: OpenApiResponse(
                description='Actions grouped by risk',
                examples=[
                    OpenApiExample(
                        'Risk Action Breakdown',
                        summary='Actions grouped by risk',
                        value={
                            'risks': [
                                {
                                    'risk': 'RISK-2024-0001',
                                    'risk_title': 'Data breach vulnerability',
                                    'count': 5,
                                    'completed_count': 2,
                                    'actions': []
                                }
                            ]
                        }
                    ),
                ]
            ),
        },
        tags=['Risk Actions'],
    )
    @action(detail=False, methods=['get'])
    def by_risk(self, request):
        """Get risk actions grouped by risk."""
        queryset = self.get_queryset()
        
        # Get all risks that have actions
        risks_with_actions = Risk.objects.filter(
            actions__in=queryset
        ).annotate(
            action_count=Count('actions', filter=Q(actions__in=queryset)),
            completed_count=Count(
                'actions',
                filter=Q(actions__in=queryset, actions__status='completed')
            )
        ).order_by('risk_id')
        
        risk_data = []
        for risk in risks_with_actions:
            risk_actions = queryset.filter(risk=risk)
            action_serializer = RiskActionListSerializer(risk_actions, many=True, context={'request': request})
            
            risk_data.append({
                'risk': risk.risk_id,
                'risk_id': risk.id,
                'risk_title': risk.title,
                'risk_level': risk.risk_level,
                'risk_level_display': risk.get_risk_level_display(),
                'count': risk.action_count,
                'completed_count': risk.completed_count,
                'actions': action_serializer.data
            })
        
        return Response({'risks': risk_data})


@extend_schema_view(
    list=extend_schema(
        summary="List reminder configurations",
        description="Retrieve risk action reminder configurations for all users.",
        tags=['Risk Action Reminders'],
    ),
    create=extend_schema(
        summary="Create reminder configuration",
        description="Create risk action reminder configuration for current user.",
        tags=['Risk Action Reminders'],
    ),
    retrieve=extend_schema(
        summary="Get reminder configuration",
        description="Retrieve detailed risk action reminder configuration.",
        tags=['Risk Action Reminders'],
    ),
    update=extend_schema(
        summary="Update reminder configuration",
        description="Update risk action reminder configuration settings.",
        tags=['Risk Action Reminders'],
    ),
)
class RiskActionReminderConfigurationViewSet(viewsets.ModelViewSet):
    """
    **Risk Action Reminder Configuration Management**
    
    Manage automated reminder settings for risk actions including:
    - Email notification preferences
    - Reminder timing and frequency
    - Weekly digest settings
    - Auto-silence options
    """
    
    serializer_class = RiskActionReminderConfigurationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return configurations, with current user's config prioritized."""
        return RiskActionReminderConfiguration.objects.select_related('user')
    
    def perform_create(self, serializer):
        """Create configuration for current user."""
        serializer.save(user=self.request.user)


@extend_schema_view(
    list=extend_schema(
        summary="Risk Analytics Dashboard",
        description="Access comprehensive risk analytics, trends, and reporting data for management dashboards and executive reporting.",
        responses={
            200: OpenApiResponse(
                description="Risk analytics data",
                examples=[
                    OpenApiExample(
                        name="Dashboard Analytics",
                        description="Complete dashboard data with risk metrics, trends, and visualizations",
                        value={
                            "risk_overview": {
                                "total_risks": 45,
                                "active_risks": 38,
                                "critical_high_risks": 12,
                                "average_risk_score": 8.5
                            },
                            "heat_map": {
                                "matrix_size": 5,
                                "total_risks": 38,
                                "heat_map": {"1": {"1": {"count": 2, "risk_level": "low"}}}
                            },
                            "trend_analysis": {
                                "creation_trend": [],
                                "closure_trend": []
                            }
                        }
                    )
                ]
            )
        }
    )
)
class RiskAnalyticsViewSet(viewsets.ViewSet):
    """
    **Risk Analytics & Reporting Dashboard**
    
    Comprehensive risk analytics and reporting capabilities providing:
    - Risk overview statistics and key performance indicators
    - Risk heat maps and trend analysis over time
    - Treatment action progress and effectiveness metrics
    - Executive summaries and governance indicators
    
    **Key Analytics Features:**
    - Risk level and status distribution analysis
    - Treatment action velocity and completion rates
    - Category-based risk exposure analysis
    - Heat map visualization for impact vs likelihood
    - Trend analysis for risk creation and closure patterns
    - Integration readiness for risk-control assessment mapping
    
    **Dashboard Data Structure:**
    All endpoints return comprehensive analytics optimized for dashboard consumption
    with real-time calculations and historical trend analysis.
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """
        Get comprehensive risk analytics dashboard data.
        
        Returns complete dashboard dataset including:
        - Risk overview statistics
        - Risk action progress metrics  
        - Heat map visualization data
        - Trend analysis and forecasting
        - Executive summary metrics
        """
        try:
            dashboard_data = RiskReportGenerator.generate_risk_dashboard_data()
            return Response(dashboard_data)
        except Exception as e:
            return Response(
                {'error': f'Failed to generate dashboard data: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def risk_overview(self, request):
        """
        Get risk overview statistics including counts, distributions, and key metrics.
        
        Provides:
        - Total and active risk counts
        - Risk level and status distributions
        - Category analysis and treatment strategy breakdown
        - Recent activity and overdue review alerts
        """
        try:
            overview_data = RiskAnalyticsService.get_risk_overview_stats()
            return Response(overview_data)
        except Exception as e:
            return Response(
                {'error': f'Failed to generate risk overview: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def action_overview(self, request):
        """
        Get risk action overview statistics and progress metrics.
        
        Provides:
        - Action counts and status distribution
        - Progress tracking and completion rates
        - Due date analysis and overdue alerts
        - Assignee workload and performance metrics
        """
        try:
            action_data = RiskAnalyticsService.get_risk_action_overview_stats()
            return Response(action_data)
        except Exception as e:
            return Response(
                {'error': f'Failed to generate action overview: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def heat_map(self, request):
        """
        Get risk heat map data for impact vs likelihood visualization.
        
        Returns matrix data showing:
        - Risk distribution across impact/likelihood combinations
        - Risk counts and levels for each matrix cell
        - Detailed risk information for drill-down analysis
        - Matrix configuration and labeling
        """
        try:
            heat_map_data = RiskAnalyticsService.get_risk_heat_map_data()
            return Response(heat_map_data)
        except Exception as e:
            return Response(
                {'error': f'Failed to generate heat map: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def trends(self, request):
        """
        Get risk trend analysis over specified time period.
        
        Query Parameters:
        - days: Number of days for trend analysis (default: 90, max: 365)
        
        Provides:
        - Risk creation and closure trends over time
        - Active risk count evolution
        - Monthly and quarterly trend analysis
        - Forecasting indicators
        """
        try:
            days = int(request.query_params.get('days', 90))
            days = min(max(30, days), 365)  # Clamp between 30 and 365 days
            
            trend_data = RiskAnalyticsService.get_risk_trend_analysis(days=days)
            return Response(trend_data)
        except ValueError:
            return Response(
                {'error': 'Invalid days parameter. Must be a number between 30 and 365.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to generate trend analysis: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def action_progress(self, request):
        """
        Get detailed risk action progress and effectiveness analysis.
        
        Provides:
        - Action velocity and completion metrics
        - Treatment effectiveness by strategy type
        - Evidence collection and validation statistics
        - Performance analysis by risk level and category
        """
        try:
            progress_data = RiskAnalyticsService.get_risk_action_progress_analysis()
            return Response(progress_data)
        except Exception as e:
            return Response(
                {'error': f'Failed to generate progress analysis: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def executive_summary(self, request):
        """
        Get executive-level risk summary for leadership reporting.
        
        Provides high-level metrics including:
        - Key risk indicators and exposure metrics
        - Quarterly trend analysis and net risk changes
        - Treatment progress and completion rates
        - Governance indicators and maturity metrics
        - Top risk areas and priority recommendations
        """
        try:
            executive_data = RiskAnalyticsService.get_executive_risk_summary()
            return Response(executive_data)
        except Exception as e:
            return Response(
                {'error': f'Failed to generate executive summary: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def control_integration(self, request):
        """
        Get risk-control integration analysis (basic version).
        
        Provides:
        - Control coverage analysis for risks
        - Gap identification by category
        - Integration readiness metrics
        
        Note: This will be enhanced with full risk-control mapping in future iterations.
        """
        try:
            integration_data = RiskAnalyticsService.get_risk_control_integration_analysis()
            return Response(integration_data)
        except Exception as e:
            return Response(
                {'error': f'Failed to generate control integration analysis: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def category_analysis(self, request):
        """
        Get detailed analysis for specific risk category or all categories.
        
        Query Parameters:
        - category_id: Specific category ID for deep dive (optional)
        
        Provides:
        - Category-specific risk metrics and breakdowns
        - Treatment analysis and action progress
        - Comparative analysis across categories
        """
        try:
            category_id = request.query_params.get('category_id')
            if category_id:
                try:
                    category_id = int(category_id)
                except ValueError:
                    return Response(
                        {'error': 'Invalid category_id parameter. Must be a number.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            category_data = RiskReportGenerator.get_risk_category_deep_dive(category_id)
            return Response(category_data)
        except Exception as e:
            return Response(
                {'error': f'Failed to generate category analysis: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )