from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from .models import Framework, Clause, Control, ControlEvidence, FrameworkMapping, ControlAssessment, AssessmentEvidence
from .serializers import (
    FrameworkListSerializer, FrameworkDetailSerializer,
    ClauseListSerializer, ClauseDetailSerializer,
    ControlListSerializer, ControlDetailSerializer, ControlCreateUpdateSerializer,
    ControlEvidenceSerializer, FrameworkMappingSerializer,
    FrameworkStatsSerializer, ControlTestingSerializer,
    ControlAssessmentListSerializer, ControlAssessmentDetailSerializer, 
    ControlAssessmentCreateUpdateSerializer, AssessmentStatusUpdateSerializer,
    BulkAssessmentCreateSerializer, AssessmentEvidenceSerializer, AssessmentProgressSerializer
)


@extend_schema_view(
    list=extend_schema(
        summary="List compliance frameworks",
        description="Retrieve a paginated list of compliance frameworks with filtering, searching, and ordering capabilities.",
        parameters=[
            OpenApiParameter(
                name='framework_type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by framework type (iso27001, nist_csf, soc2, etc.)'
            ),
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by framework status (active, draft, archived)'
            ),
            OpenApiParameter(
                name='is_mandatory',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter by mandatory status'
            ),
            OpenApiParameter(
                name='active_only',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Show only active frameworks'
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search across name, short_name, description, and issuing_organization'
            ),
            OpenApiParameter(
                name='ordering',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Order by: name, version, effective_date, created_at (prefix with - for descending)'
            ),
        ],
        tags=['Frameworks'],
        examples=[
            OpenApiExample(
                'List active frameworks',
                summary='Get active ISO 27001 frameworks',
                description='Example of filtering for active ISO 27001 frameworks',
                value='?framework_type=iso27001&status=active'
            ),
        ]
    ),
    create=extend_schema(
        summary="Create new compliance framework",
        description="Create a new compliance framework with all required metadata and configuration.",
        tags=['Frameworks'],
    ),
    retrieve=extend_schema(
        summary="Get framework details",
        description="Retrieve detailed information about a specific compliance framework including metadata and configuration.",
        tags=['Frameworks'],
    ),
    update=extend_schema(
        summary="Update framework",
        description="Update an existing compliance framework. Requires all fields.",
        tags=['Frameworks'],
    ),
    partial_update=extend_schema(
        summary="Partially update framework",
        description="Update specific fields of an existing compliance framework.",
        tags=['Frameworks'],
    ),
    destroy=extend_schema(
        summary="Delete framework",
        description="Delete a compliance framework. This will also remove all associated clauses and mappings.",
        tags=['Frameworks'],
    ),
)
class FrameworkViewSet(viewsets.ModelViewSet):
    """
    **Compliance Framework Management**
    
    This ViewSet provides comprehensive management of compliance frameworks including:
    - Full CRUD operations for framework lifecycle management
    - Framework-specific data retrieval (clauses, controls, statistics)
    - Advanced filtering and search capabilities
    - Framework status and metadata management
    
    **Key Features:**
    - Support for major frameworks (ISO 27001, NIST CSF, SOC 2, etc.)
    - Framework versioning and effective date tracking
    - Integration with clause and control management
    - Statistical reporting and analytics
    
    **Common Use Cases:**
    - Import new compliance frameworks
    - Track framework versions and updates
    - Analyze framework coverage and implementation
    - Generate framework-specific reports
    """
    queryset = Framework.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['framework_type', 'status', 'is_mandatory']
    search_fields = ['name', 'short_name', 'description', 'issuing_organization']
    ordering_fields = ['name', 'version', 'effective_date', 'created_at']
    ordering = ['name', '-version']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return FrameworkListSerializer
        return FrameworkDetailSerializer
    
    def get_queryset(self):
        queryset = Framework.objects.select_related('created_by')
        
        # Filter by active status if requested
        if self.request.query_params.get('active_only', '').lower() == 'true':
            queryset = queryset.filter(status='active')
        
        return queryset
    
    @extend_schema(
        summary="Get framework clauses",
        description="Retrieve all clauses associated with a specific framework with optional filtering by clause type and criticality.",
        parameters=[
            OpenApiParameter(
                name='clause_type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by clause type (control, guidance, requirement, etc.)'
            ),
            OpenApiParameter(
                name='criticality',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by criticality level (low, medium, high, critical)'
            ),
        ],
        responses={
            200: ClauseListSerializer(many=True),
            404: OpenApiResponse(description='Framework not found'),
        },
        tags=['Frameworks'],
    )
    @action(detail=True, methods=['get'])
    def clauses(self, request, pk=None):
        """Get all clauses for a specific framework with optional filtering."""
        framework = self.get_object()
        clauses = framework.clauses.all().order_by('sort_order', 'clause_id')
        
        # Apply filtering
        clause_type = request.query_params.get('clause_type')
        if clause_type:
            clauses = clauses.filter(clause_type=clause_type)
        
        criticality = request.query_params.get('criticality')
        if criticality:
            clauses = clauses.filter(criticality=criticality)
        
        serializer = ClauseListSerializer(clauses, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Get framework controls",
        description="Retrieve all controls mapped to a specific framework through clause relationships.",
        responses={
            200: ControlListSerializer(many=True),
            404: OpenApiResponse(description='Framework not found'),
        },
        tags=['Frameworks'],
    )
    @action(detail=True, methods=['get'])
    def controls(self, request, pk=None):
        """Get all controls mapped to a specific framework."""
        framework = self.get_object()
        controls = Control.objects.filter(
            clauses__framework=framework
        ).distinct().select_related('control_owner', 'created_by')
        
        serializer = ControlListSerializer(controls, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Get framework statistics",
        description="Retrieve comprehensive statistics for a specific framework including clause counts, control distribution, and testing status.",
        responses={
            200: OpenApiResponse(
                description='Framework statistics',
                examples=[
                    OpenApiExample(
                        'Framework Statistics',
                        summary='Example framework statistics response',
                        description='Comprehensive statistics for ISO 27001 framework',
                        value={
                            'framework_id': 1,
                            'framework_name': 'ISO 27001:2022',
                            'total_clauses': 114,
                            'total_controls': 93,
                            'active_controls': 89,
                            'controls_needing_testing': 12,
                            'clause_types': {'control': 93, 'guidance': 21},
                            'control_statuses': {'active': 89, 'draft': 4}
                        }
                    ),
                ]
            ),
            404: OpenApiResponse(description='Framework not found'),
        },
        tags=['Frameworks'],
    )
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get comprehensive statistics for a specific framework."""
        framework = self.get_object()
        
        total_clauses = framework.clauses.count()
        total_controls = Control.objects.filter(clauses__framework=framework).distinct().count()
        active_controls = Control.objects.filter(
            clauses__framework=framework, status='active'
        ).distinct().count()
        controls_needing_testing = Control.objects.filter(
            clauses__framework=framework
        ).distinct().filter(
            Q(last_tested_date__isnull=True) |
            Q(last_tested_date__lt=timezone.now().date() - timezone.timedelta(days=90))
        ).count()
        
        clause_types = framework.clauses.values('clause_type').annotate(
            count=Count('id')
        ).order_by('clause_type')
        
        control_statuses = Control.objects.filter(
            clauses__framework=framework
        ).distinct().values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        stats = {
            'framework_id': framework.id,
            'framework_name': framework.name,
            'total_clauses': total_clauses,
            'total_controls': total_controls,
            'active_controls': active_controls,
            'controls_needing_testing': controls_needing_testing,
            'clause_types': {item['clause_type']: item['count'] for item in clause_types},
            'control_statuses': {item['status']: item['count'] for item in control_statuses}
        }
        
        return Response(stats)


class ClauseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing framework clauses.
    Provides CRUD operations and clause-specific endpoints.
    """
    queryset = Clause.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['framework', 'clause_type', 'criticality', 'is_testable', 'parent_clause']
    search_fields = ['clause_id', 'title', 'description']
    ordering_fields = ['sort_order', 'clause_id', 'created_at']
    ordering = ['framework', 'sort_order', 'clause_id']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ClauseListSerializer
        return ClauseDetailSerializer
    
    def get_queryset(self):
        queryset = Clause.objects.select_related('framework', 'parent_clause')
        
        # Filter by framework if specified
        framework_id = self.request.query_params.get('framework')
        if framework_id:
            queryset = queryset.filter(framework_id=framework_id)
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def controls(self, request, pk=None):
        """Get all controls mapped to a specific clause."""
        clause = self.get_object()
        controls = clause.controls.all().select_related('control_owner', 'created_by')
        
        serializer = ControlListSerializer(controls, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def subclauses(self, request, pk=None):
        """Get all subclauses for a specific clause."""
        clause = self.get_object()
        subclauses = clause.subclauses.all().order_by('sort_order', 'clause_id')
        
        serializer = ClauseListSerializer(subclauses, many=True)
        return Response(serializer.data)


class ControlViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing controls.
    Provides CRUD operations and control-specific endpoints.
    """
    queryset = Control.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'control_type', 'automation_level', 'status', 'control_owner',
        'effectiveness_rating', 'last_test_result', 'risk_rating'
    ]
    search_fields = ['control_id', 'name', 'description', 'business_owner']
    ordering_fields = ['control_id', 'name', 'last_tested_date', 'created_at']
    ordering = ['control_id']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ControlListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ControlCreateUpdateSerializer
        return ControlDetailSerializer
    
    def get_queryset(self):
        queryset = Control.objects.select_related(
            'control_owner', 'created_by'
        ).prefetch_related('clauses__framework')
        
        # Filter by framework if specified
        framework_id = self.request.query_params.get('framework')
        if framework_id:
            queryset = queryset.filter(clauses__framework_id=framework_id).distinct()
        
        # Filter by testing status
        needs_testing = self.request.query_params.get('needs_testing')
        if needs_testing == 'true':
            queryset = queryset.filter(
                Q(last_tested_date__isnull=True) |
                Q(last_tested_date__lt=timezone.now().date() - timezone.timedelta(days=90))
            )
        
        # Filter by active status
        active_only = self.request.query_params.get('active_only')
        if active_only == 'true':
            queryset = queryset.filter(status='active')
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def update_testing(self, request, pk=None):
        """Update control testing results."""
        control = self.get_object()
        serializer = ControlTestingSerializer(
            data=request.data, 
            context={'request': request}
        )
        
        if serializer.is_valid():
            updated_control = serializer.update_control_testing(control)
            response_serializer = ControlDetailSerializer(updated_control)
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def evidence(self, request, pk=None):
        """Get all evidence for a specific control."""
        control = self.get_object()
        evidence = control.evidence.all().select_related(
            'collected_by', 'validated_by', 'document'
        ).order_by('-evidence_date')
        
        serializer = ControlEvidenceSerializer(evidence, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def needing_testing(self, request):
        """Get all controls that need testing."""
        controls = self.get_queryset().filter(
            Q(last_tested_date__isnull=True) |
            Q(last_tested_date__lt=timezone.now().date() - timezone.timedelta(days=90))
        )
        
        serializer = ControlListSerializer(controls, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_effectiveness(self, request):
        """Get controls grouped by effectiveness rating."""
        effectiveness_groups = {}
        
        for rating, display in Control.EFFECTIVENESS_RATINGS:
            controls = self.get_queryset().filter(effectiveness_rating=rating)
            effectiveness_groups[rating] = {
                'display_name': display,
                'count': controls.count(),
                'controls': ControlListSerializer(controls[:10], many=True).data  # Limit for performance
            }
        
        return Response(effectiveness_groups)


class ControlEvidenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing control evidence.
    """
    queryset = ControlEvidence.objects.all()
    serializer_class = ControlEvidenceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['control', 'evidence_type', 'is_validated', 'collected_by']
    search_fields = ['title', 'description']
    ordering_fields = ['evidence_date', 'created_at']
    ordering = ['-evidence_date']
    
    def get_queryset(self):
        return ControlEvidence.objects.select_related(
            'control', 'collected_by', 'validated_by', 'document'
        )
    
    def perform_create(self, serializer):
        serializer.save(collected_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def validate_evidence(self, request, pk=None):
        """Validate a piece of evidence."""
        evidence = self.get_object()
        notes = request.data.get('notes', '')
        
        evidence.validate_evidence(request.user, notes)
        
        serializer = self.get_serializer(evidence)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def assessments(self, request, pk=None):
        """Get all assessments that use this evidence."""
        evidence = self.get_object()
        
        assessment_links = AssessmentEvidence.objects.select_related(
            'assessment',
            'assessment__control',
            'created_by'
        ).filter(evidence=evidence)
        
        assessments_data = []
        for link in assessment_links:
            assessments_data.append({
                'assessment_id': link.assessment.id,
                'assessment_identifier': link.assessment.assessment_id,
                'control_id': link.assessment.control.control_id,
                'control_name': link.assessment.control.name,
                'assessment_status': link.assessment.status,
                'evidence_purpose': link.evidence_purpose,
                'is_primary_evidence': link.is_primary_evidence,
                'linked_by': link.created_by.username if link.created_by else None,
                'linked_at': link.created_at
            })
        
        return Response({
            'evidence_id': evidence.id,
            'evidence_title': evidence.title,
            'usage_count': assessment_links.count(),
            'assessments': assessments_data
        })


class FrameworkMappingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing framework mappings.
    """
    queryset = FrameworkMapping.objects.all()
    serializer_class = FrameworkMappingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['mapping_type', 'source_clause__framework', 'target_clause__framework']
    search_fields = ['mapping_rationale']
    ordering_fields = ['confidence_level', 'created_at']
    ordering = ['-confidence_level']
    
    def get_queryset(self):
        return FrameworkMapping.objects.select_related(
            'source_clause__framework', 'target_clause__framework',
            'created_by', 'verified_by'
        )
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


@action(detail=False, methods=['get'])
def framework_stats(request):
    """Get overall framework catalog statistics."""
    total_frameworks = Framework.objects.count()
    active_frameworks = Framework.objects.filter(status='active').count()
    total_clauses = Clause.objects.count()
    total_controls = Control.objects.count()
    active_controls = Control.objects.filter(status='active').count()
    controls_needing_testing = Control.objects.filter(
        Q(last_tested_date__isnull=True) |
        Q(last_tested_date__lt=timezone.now().date() - timezone.timedelta(days=90))
    ).count()
    
    framework_types = Framework.objects.values('framework_type').annotate(
        count=Count('id')
    ).order_by('framework_type')
    
    control_effectiveness = Control.objects.filter(
        effectiveness_rating__isnull=False
    ).values('effectiveness_rating').annotate(
        count=Count('id')
    ).order_by('effectiveness_rating')
    
    stats = {
        'total_frameworks': total_frameworks,
        'active_frameworks': active_frameworks,
        'total_clauses': total_clauses,
        'total_controls': total_controls,
        'active_controls': active_controls,
        'controls_needing_testing': controls_needing_testing,
        'framework_types': {item['framework_type']: item['count'] for item in framework_types},
        'control_effectiveness': {item['effectiveness_rating']: item['count'] for item in control_effectiveness}
    }
    
    serializer = FrameworkStatsSerializer(stats)
    return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        summary="List control assessments",
        description="Retrieve a paginated list of control assessments with comprehensive filtering, searching, and ordering capabilities.",
        parameters=[
            OpenApiParameter(
                name='framework',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by framework ID'
            ),
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by assessment status (not_started, pending, in_progress, under_review, complete, not_applicable)'
            ),
            OpenApiParameter(
                name='applicability',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by applicability (applicable, not_applicable, conditional)'
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
                description='Show only overdue assessments'
            ),
            OpenApiParameter(
                name='completed',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter by completion status'
            ),
            OpenApiParameter(
                name='my_assignments',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Show only assessments assigned to current user'
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search across assessment_id, control_id, control_name, and assessment_notes'
            ),
        ],
        tags=['Assessments'],
        examples=[
            OpenApiExample(
                'My overdue assessments',
                summary='Get current user\'s overdue assessments',
                description='Example of filtering for current user\'s overdue assessments',
                value='?my_assignments=true&overdue=true'
            ),
        ]
    ),
    create=extend_schema(
        summary="Create control assessment",
        description="Create a new control assessment with all required metadata and assignment information.",
        tags=['Assessments'],
    ),
    retrieve=extend_schema(
        summary="Get assessment details",
        description="Retrieve detailed information about a specific control assessment including evidence links and progress.",
        tags=['Assessments'],
    ),
    update=extend_schema(
        summary="Update assessment",
        description="Update an existing control assessment. Requires all fields.",
        tags=['Assessments'],
    ),
    partial_update=extend_schema(
        summary="Partially update assessment",
        description="Update specific fields of an existing control assessment.",
        tags=['Assessments'],
    ),
    destroy=extend_schema(
        summary="Delete assessment",
        description="Delete a control assessment and all associated evidence links.",
        tags=['Assessments'],
    ),
)
class ControlAssessmentViewSet(viewsets.ModelViewSet):
    """
    **Control Assessment Management**
    
    This ViewSet provides comprehensive management of control assessments including:
    - Full assessment lifecycle management (creation, assignment, completion)
    - Evidence management and linking capabilities
    - Status tracking and progress monitoring
    - Bulk operations for efficiency
    - Advanced filtering and search capabilities
    
    **Key Features:**
    - Support for various assessment statuses and workflows
    - Evidence upload and linking with file management
    - Bulk assessment creation for frameworks
    - Progress tracking and reporting
    - Assignment management and notifications
    
    **Assessment Workflow:**
    1. Create assessment (manual or bulk)
    2. Assign to assessor
    3. Collect and link evidence
    4. Update status and notes
    5. Review and complete
    
    **Common Use Cases:**
    - Conduct periodic control assessments
    - Track assessment progress across frameworks
    - Manage evidence collection and validation
    - Generate assessment reports and metrics
    """
    queryset = ControlAssessment.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'applicability', 'status', 'implementation_status', 'assigned_to',
        'reviewer', 'risk_rating', 'control', 'control__clauses__framework'
    ]
    search_fields = ['assessment_id', 'control__control_id', 'control__name', 'assessment_notes']
    ordering_fields = ['due_date', 'created_at', 'updated_at', 'completion_percentage']
    ordering = ['due_date', 'control__control_id']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ControlAssessmentListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ControlAssessmentCreateUpdateSerializer
        return ControlAssessmentDetailSerializer
    
    def get_queryset(self):
        queryset = ControlAssessment.objects.select_related(
            'control', 'assigned_to', 'reviewer', 'remediation_owner', 'created_by'
        ).prefetch_related('control__clauses__framework', 'evidence_links__evidence')
        
        # Filter by framework if specified
        framework_id = self.request.query_params.get('framework')
        if framework_id:
            queryset = queryset.filter(control__clauses__framework_id=framework_id).distinct()
        
        # Filter by overdue status
        overdue = self.request.query_params.get('overdue')
        if overdue == 'true':
            today = timezone.now().date()
            queryset = queryset.filter(
                due_date__lt=today,
                status__in=['not_started', 'pending', 'in_progress', 'under_review']
            )
        
        # Filter by completion status
        completed = self.request.query_params.get('completed')
        if completed == 'true':
            queryset = queryset.filter(status='complete')
        elif completed == 'false':
            queryset = queryset.exclude(status__in=['complete', 'not_applicable'])
        
        # Filter by assigned user
        my_assignments = self.request.query_params.get('my_assignments')
        if my_assignments == 'true':
            queryset = queryset.filter(assigned_to=self.request.user)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update assessment status with notes."""
        assessment = self.get_object()
        serializer = AssessmentStatusUpdateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            updated_assessment = serializer.update_assessment_status(assessment)
            response_serializer = ControlAssessmentDetailSerializer(updated_assessment)
            return Response(response_serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def evidence(self, request, pk=None):
        """Get all evidence linked to this assessment."""
        assessment = self.get_object()
        evidence_links = assessment.evidence_links.all().select_related('evidence', 'created_by')
        
        serializer = AssessmentEvidenceSerializer(evidence_links, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def link_evidence(self, request, pk=None):
        """Link evidence to this assessment."""
        assessment = self.get_object()
        data = request.data.copy()
        data['assessment'] = assessment.id
        
        serializer = AssessmentEvidenceSerializer(
            data=data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Upload evidence to assessment",
        description="Upload a file as evidence and link it directly to this assessment. Creates document, evidence, and assessment link in one operation.",
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {'type': 'string', 'format': 'binary'},
                    'title': {'type': 'string', 'description': 'Document title'},
                    'description': {'type': 'string', 'description': 'Document description'},
                    'evidence_title': {'type': 'string', 'description': 'Evidence title'},
                    'evidence_type': {'type': 'string', 'description': 'Evidence type'},
                    'evidence_description': {'type': 'string', 'description': 'Evidence description'},
                    'evidence_purpose': {'type': 'string', 'description': 'Purpose of evidence'},
                    'is_primary_evidence': {'type': 'boolean', 'description': 'Is primary evidence'},
                    'evidence_date': {'type': 'string', 'format': 'date', 'description': 'Evidence date'},
                }
            }
        },
        responses={
            201: OpenApiResponse(
                description='Evidence uploaded and linked successfully',
                examples=[
                    OpenApiExample(
                        'Successful Upload',
                        summary='Evidence upload success response',
                        description='Response when evidence is successfully uploaded and linked',
                        value={
                            'message': 'Evidence uploaded and linked to assessment successfully',
                            'document': {
                                'id': 123,
                                'title': 'Network Security Policy.pdf',
                                'file_url': '/media/documents/network_policy.pdf',
                                'file_size': 2048576
                            },
                            'evidence': {
                                'id': 456,
                                'title': 'Network Security Policy Evidence',
                                'evidence_type': 'document'
                            },
                            'assessment_link': {
                                'id': 789,
                                'evidence_purpose': 'Policy documentation'
                            }
                        }
                    ),
                ]
            ),
            400: OpenApiResponse(description='Bad request - file missing or invalid data'),
            404: OpenApiResponse(description='Assessment not found'),
        },
        tags=['Assessments'],
    )
    @action(detail=True, methods=['post'])
    def upload_evidence(self, request, pk=None):
        """Upload evidence file directly to this assessment with automatic linking."""
        assessment = self.get_object()
        
        # Extract file and metadata from request
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({
                'error': 'No file provided. Please include a file in the request.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create document first
        from core.models import Document
        document = Document.objects.create(
            title=request.data.get('title', uploaded_file.name),
            description=request.data.get('description', ''),
            file=uploaded_file,
            uploaded_by=request.user
        )
        
        # Create evidence linked to the control
        evidence_data = {
            'title': request.data.get('evidence_title', document.title),
            'evidence_type': request.data.get('evidence_type', 'document'),
            'description': request.data.get('evidence_description', ''),
            'document': document.id,
            'evidence_date': request.data.get('evidence_date', timezone.now().date()),
        }
        
        evidence_serializer = ControlEvidenceSerializer(
            data=evidence_data,
            context={'request': request}
        )
        
        if not evidence_serializer.is_valid():
            # Clean up document if evidence creation fails
            document.delete()
            return Response(evidence_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Save evidence with control relationship
        evidence = evidence_serializer.save(
            control=assessment.control,
            collected_by=request.user
        )
        
        # Link evidence to assessment
        assessment_evidence_data = {
            'assessment': assessment.id,
            'evidence': evidence.id,
            'evidence_purpose': request.data.get('evidence_purpose', 'Assessment evidence'),
            'is_primary_evidence': request.data.get('is_primary_evidence', False)
        }
        
        link_serializer = AssessmentEvidenceSerializer(
            data=assessment_evidence_data,
            context={'request': request}
        )
        
        if link_serializer.is_valid():
            link_serializer.save()
            
            # Return complete evidence information
            return Response({
                'message': 'Evidence uploaded and linked to assessment successfully',
                'document': {
                    'id': document.id,
                    'title': document.title,
                    'file_url': document.file_url,
                    'file_size': document.file_size
                },
                'evidence': evidence_serializer.data,
                'assessment_link': link_serializer.data
            }, status=status.HTTP_201_CREATED)
        else:
            # Clean up if linking fails
            evidence.delete()
            document.delete()
            return Response(link_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def evidence(self, request, pk=None):
        """Get all evidence linked to this assessment."""
        assessment = self.get_object()
        
        # Get assessment evidence links with related evidence
        evidence_links = AssessmentEvidence.objects.select_related(
            'evidence',
            'evidence__document',
            'evidence__collected_by',
            'evidence__validated_by',
            'created_by'
        ).filter(assessment=assessment)
        
        serializer = AssessmentEvidenceSerializer(evidence_links, many=True)
        
        return Response({
            'assessment_id': assessment.id,
            'assessment_control': assessment.control.control_id,
            'evidence_count': evidence_links.count(),
            'evidence': serializer.data
        })
    
    @action(detail=True, methods=['delete'])
    def remove_evidence(self, request, pk=None):
        """Remove evidence link from this assessment."""
        assessment = self.get_object()
        evidence_id = request.data.get('evidence_id')
        
        if not evidence_id:
            return Response({
                'error': 'evidence_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            evidence_link = AssessmentEvidence.objects.get(
                assessment=assessment,
                evidence_id=evidence_id
            )
            evidence_link.delete()
            
            return Response({
                'message': 'Evidence removed from assessment successfully'
            }, status=status.HTTP_200_OK)
            
        except AssessmentEvidence.DoesNotExist:
            return Response({
                'error': 'Evidence link not found for this assessment'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def bulk_upload_evidence(self, request, pk=None):
        """Upload multiple evidence files to this assessment."""
        assessment = self.get_object()
        
        uploaded_files = request.FILES.getlist('files')
        if not uploaded_files:
            return Response({
                'error': 'No files provided. Please include files in the request.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Process each file
        results = []
        errors = []
        
        for i, uploaded_file in enumerate(uploaded_files):
            try:
                # Create document
                from core.models import Document
                document = Document.objects.create(
                    title=request.data.get(f'title_{i}', uploaded_file.name),
                    description=request.data.get(f'description_{i}', ''),
                    file=uploaded_file,
                    uploaded_by=request.user
                )
                
                # Create evidence
                evidence = ControlEvidence.objects.create(
                    control=assessment.control,
                    title=request.data.get(f'evidence_title_{i}', document.title),
                    evidence_type=request.data.get(f'evidence_type_{i}', 'document'),
                    description=request.data.get(f'evidence_description_{i}', ''),
                    document=document,
                    evidence_date=timezone.now().date(),
                    collected_by=request.user
                )
                
                # Link to assessment
                assessment_evidence = AssessmentEvidence.objects.create(
                    assessment=assessment,
                    evidence=evidence,
                    evidence_purpose=request.data.get(f'evidence_purpose_{i}', 'Assessment evidence'),
                    is_primary_evidence=False,
                    created_by=request.user
                )
                
                results.append({
                    'file_name': uploaded_file.name,
                    'document_id': document.id,
                    'evidence_id': evidence.id,
                    'assessment_link_id': assessment_evidence.id,
                    'status': 'success'
                })
                
            except Exception as e:
                errors.append({
                    'file_name': uploaded_file.name,
                    'error': str(e),
                    'status': 'failed'
                })
        
        return Response({
            'message': f'Processed {len(uploaded_files)} files',
            'successful_uploads': len(results),
            'failed_uploads': len(errors),
            'results': results,
            'errors': errors
        }, status=status.HTTP_201_CREATED if results else status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Bulk create assessments",
        description="Create multiple control assessments in bulk for a specific framework. Automatically creates assessments for all controls in the framework.",
        request=BulkAssessmentCreateSerializer,
        responses={
            201: OpenApiResponse(
                description='Assessments created successfully',
                examples=[
                    OpenApiExample(
                        'Bulk Creation Success',
                        summary='Successful bulk assessment creation',
                        description='Response when assessments are successfully created in bulk',
                        value={
                            'message': 'Created 93 assessments',
                            'created_count': 93,
                            'assessments': [
                                {
                                    'id': 1,
                                    'assessment_id': 'ASSESS-001',
                                    'control': {'control_id': 'A.5.1.1', 'name': 'Information security policy'},
                                    'status': 'not_started',
                                    'assigned_to': {'username': 'assessor1', 'full_name': 'John Assessor'},
                                    'due_date': '2024-03-15'
                                }
                            ]
                        }
                    ),
                ]
            ),
            400: OpenApiResponse(description='Bad request - invalid framework or data'),
        },
        tags=['Assessments'],
    )
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Create multiple control assessments in bulk for a framework."""
        serializer = BulkAssessmentCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            created_assessments = serializer.create_bulk_assessments()
            response_serializer = ControlAssessmentListSerializer(created_assessments, many=True)
            return Response({
                'message': f'Created {len(created_assessments)} assessments',
                'created_count': len(created_assessments),
                'assessments': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get all overdue assessments."""
        today = timezone.now().date()
        assessments = self.get_queryset().filter(
            due_date__lt=today,
            status__in=['not_started', 'pending', 'in_progress', 'under_review']
        )
        
        serializer = ControlAssessmentListSerializer(assessments, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_assignments(self, request):
        """Get assessments assigned to current user."""
        assessments = self.get_queryset().filter(assigned_to=request.user)
        
        serializer = ControlAssessmentListSerializer(assessments, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Get assessment progress report",
        description="Generate comprehensive progress report with statistics, breakdowns, and upcoming deadlines. Optionally filter by framework.",
        parameters=[
            OpenApiParameter(
                name='framework',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter progress report by specific framework ID'
            ),
        ],
        responses={
            200: AssessmentProgressSerializer,
        },
        tags=['Assessments'],
        examples=[
            OpenApiExample(
                'Progress Report',
                summary='Assessment progress report example',
                description='Comprehensive progress report with statistics and breakdowns',
                value={
                    'framework_id': 1,
                    'total_assessments': 93,
                    'completed_assessments': 67,
                    'overdue_assessments': 5,
                    'completion_percentage': 72.0,
                    'status_breakdown': {
                        'complete': {'display': 'Complete', 'count': 67},
                        'in_progress': {'display': 'In Progress', 'count': 21},
                        'overdue': {'display': 'Overdue', 'count': 5}
                    },
                    'upcoming_due_dates': [
                        {
                            'assessment_id': 'ASSESS-089',
                            'control_id': 'A.8.1.2',
                            'due_date': '2024-03-20',
                            'days_until_due': 5
                        }
                    ]
                }
            ),
        ]
    )
    @action(detail=False, methods=['get'])
    def progress_report(self, request):
        """Generate comprehensive assessment progress report with statistics and analytics."""
        queryset = self.get_queryset()
        framework_id = request.query_params.get('framework')
        
        if framework_id:
            queryset = queryset.filter(control__clauses__framework_id=framework_id).distinct()
        
        # Calculate statistics
        total_assessments = queryset.count()
        completed_assessments = queryset.filter(status='complete').count()
        overdue_assessments = queryset.filter(
            due_date__lt=timezone.now().date(),
            status__in=['not_started', 'pending', 'in_progress', 'under_review']
        ).count()
        
        completion_percentage = (completed_assessments / total_assessments * 100) if total_assessments > 0 else 0
        
        # Status breakdown
        status_breakdown = {}
        for status_choice, display in ControlAssessment.STATUS_CHOICES:
            count = queryset.filter(status=status_choice).count()
            status_breakdown[status_choice] = {'display': display, 'count': count}
        
        # Applicability breakdown
        applicability_breakdown = {}
        for app_choice, display in ControlAssessment.APPLICABILITY_CHOICES:
            count = queryset.filter(applicability=app_choice).count()
            applicability_breakdown[app_choice] = {'display': display, 'count': count}
        
        # Risk breakdown
        risk_breakdown = {}
        for risk_choice, display in [('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')]:
            count = queryset.filter(risk_rating=risk_choice).count()
            risk_breakdown[risk_choice] = {'display': display, 'count': count}
        
        # Upcoming due dates (next 30 days)
        upcoming = queryset.filter(
            due_date__gte=timezone.now().date(),
            due_date__lte=timezone.now().date() + timezone.timedelta(days=30),
            status__in=['not_started', 'pending', 'in_progress', 'under_review']
        ).order_by('due_date')
        
        upcoming_due_dates = []
        for assessment in upcoming[:10]:  # Limit to top 10
            upcoming_due_dates.append({
                'assessment_id': assessment.assessment_id,
                'control_id': assessment.control.control_id,
                'due_date': assessment.due_date,
                'days_until_due': assessment.days_until_due,
                'assigned_to': assessment.assigned_to.get_full_name() if assessment.assigned_to else None
            })
        
        # Assignments by user
        assignments_by_user = {}
        user_assignments = queryset.filter(assigned_to__isnull=False).values(
            'assigned_to__username', 'assigned_to__first_name', 'assigned_to__last_name'
        ).annotate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='complete')),
            overdue=Count('id', filter=Q(
                due_date__lt=timezone.now().date(),
                status__in=['not_started', 'pending', 'in_progress', 'under_review']
            ))
        )
        
        for user_data in user_assignments:
            username = user_data['assigned_to__username']
            full_name = f"{user_data['assigned_to__first_name']} {user_data['assigned_to__last_name']}".strip()
            assignments_by_user[username] = {
                'full_name': full_name or username,
                'total': user_data['total'],
                'completed': user_data['completed'],
                'overdue': user_data['overdue']
            }
        
        progress_data = {
            'framework_id': int(framework_id) if framework_id else None,
            'total_assessments': total_assessments,
            'completed_assessments': completed_assessments,
            'overdue_assessments': overdue_assessments,
            'completion_percentage': round(completion_percentage, 1),
            'status_breakdown': status_breakdown,
            'applicability_breakdown': applicability_breakdown,
            'risk_breakdown': risk_breakdown,
            'upcoming_due_dates': upcoming_due_dates,
            'assignments_by_user': assignments_by_user
        }
        
        serializer = AssessmentProgressSerializer(progress_data)
        return Response(serializer.data)


class AssessmentEvidenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing assessment evidence links.
    """
    queryset = AssessmentEvidence.objects.all()
    serializer_class = AssessmentEvidenceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['assessment', 'evidence', 'is_primary_evidence']
    search_fields = ['evidence_purpose', 'evidence__title']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return AssessmentEvidence.objects.select_related(
            'assessment', 'evidence', 'created_by'
        )
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)