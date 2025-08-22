from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from django.utils import timezone
from .models import Framework, Clause, Control, ControlEvidence, FrameworkMapping
from .serializers import (
    FrameworkListSerializer, FrameworkDetailSerializer,
    ClauseListSerializer, ClauseDetailSerializer,
    ControlListSerializer, ControlDetailSerializer, ControlCreateUpdateSerializer,
    ControlEvidenceSerializer, FrameworkMappingSerializer,
    FrameworkStatsSerializer, ControlTestingSerializer
)


class FrameworkViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing compliance frameworks.
    Provides CRUD operations and additional framework-specific endpoints.
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
    
    @action(detail=True, methods=['get'])
    def clauses(self, request, pk=None):
        """Get all clauses for a specific framework."""
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
    
    @action(detail=True, methods=['get'])
    def controls(self, request, pk=None):
        """Get all controls mapped to a specific framework."""
        framework = self.get_object()
        controls = Control.objects.filter(
            clauses__framework=framework
        ).distinct().select_related('control_owner', 'created_by')
        
        serializer = ControlListSerializer(controls, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get statistics for a specific framework."""
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