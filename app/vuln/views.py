from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ScanJob, ScanSchedule, ScanTarget, VulnerabilityFinding
from .serializers import (
    ScanJobSerializer,
    ScanScheduleSerializer,
    ScanTargetSerializer,
    VulnerabilityFindingSerializer,
)
from .services import (
    advance_schedule_after_queue,
    create_risk_action_from_finding,
    create_risk_from_finding,
    create_scan_job,
    export_findings_csv,
)
from .tasks import run_scan_job


class ScanTargetViewSet(viewsets.ModelViewSet):
    serializer_class = ScanTargetSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['target_type', 'status', 'owner']
    search_fields = ['name', 'address']
    ordering_fields = ['name', 'status', 'created_at', 'updated_at']
    ordering = ['name']

    def get_queryset(self):
        return ScanTarget.objects.select_related('owner', 'created_by')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='start-scan')
    def start_scan(self, request, pk=None):
        target = self.get_object()
        try:
            job = create_scan_job(target, requested_by=request.user)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        schema_name = getattr(getattr(request, 'tenant', None), 'schema_name', None)
        run_scan_job.delay(str(job.id), schema_name)
        return Response(ScanJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


class ScanScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = ScanScheduleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['target', 'frequency', 'is_active']
    ordering_fields = ['next_run_at', 'name', 'created_at']
    ordering = ['next_run_at', 'name']

    def get_queryset(self):
        return ScanSchedule.objects.select_related('target', 'created_by')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['post'], url_path='run-due')
    def run_due(self, request):
        due_schedules = self.get_queryset().filter(
            is_active=True,
            next_run_at__lte=timezone.now(),
            target__status='approved',
        )
        queued = 0
        schema_name = getattr(getattr(request, 'tenant', None), 'schema_name', None)
        for schedule in due_schedules:
            job = create_scan_job(schedule.target, requested_by=request.user, schedule=schedule)
            advance_schedule_after_queue(schedule)
            run_scan_job.delay(str(job.id), schema_name)
            queued += 1
        return Response({'queued': queued}, status=status.HTTP_202_ACCEPTED)


class ScanJobViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ScanJobSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['target', 'scanner', 'status']
    ordering_fields = ['created_at', 'started_at', 'finished_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return ScanJob.objects.select_related('target', 'schedule', 'requested_by')

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        job = self.get_object()
        if job.status not in {'failed', 'cancelled'}:
            return Response({'detail': 'Only failed or cancelled jobs can be retried.'}, status=status.HTTP_400_BAD_REQUEST)
        retry_job = create_scan_job(job.target, requested_by=request.user, schedule=job.schedule, scanner=job.scanner)
        schema_name = getattr(getattr(request, 'tenant', None), 'schema_name', None)
        run_scan_job.delay(str(retry_job.id), schema_name)
        return Response(ScanJobSerializer(retry_job).data, status=status.HTTP_202_ACCEPTED)


class VulnerabilityFindingViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = VulnerabilityFindingSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch', 'post', 'head', 'options']
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['target', 'severity', 'status', 'scanner_name']
    search_fields = ['title', 'description', 'cve', 'matched_at', 'template_id']
    ordering_fields = ['severity', 'last_seen_at', 'first_seen_at', 'updated_at']
    ordering = ['severity', '-last_seen_at']

    def get_queryset(self):
        return VulnerabilityFinding.objects.select_related('target', 'job', 'risk', 'risk_action')

    @action(detail=True, methods=['post'], url_path='create-risk')
    def create_risk(self, request, pk=None):
        finding = self.get_object()
        if finding.risk:
            return Response({'detail': 'Finding is already linked to a risk.', 'risk': finding.risk.id})
        risk = create_risk_from_finding(finding, user=request.user)
        return Response({'risk': risk.id, 'risk_id': risk.risk_id}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='create-risk-action')
    def create_risk_action(self, request, pk=None):
        finding = self.get_object()
        if finding.risk_action:
            return Response({'detail': 'Finding is already linked to a risk action.', 'risk_action': finding.risk_action.id})
        action = create_risk_action_from_finding(finding, user=request.user)
        return Response({'risk_action': action.id, 'action_id': action.action_id}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='export')
    def export(self, request):
        content = export_findings_csv(self.filter_queryset(self.get_queryset()))
        response = HttpResponse(content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=\"vulnerability-findings.csv\"'
        return response
