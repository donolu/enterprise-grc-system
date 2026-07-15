"""
Policy Repository Views

Comprehensive API endpoints for policy management, versioning, and acknowledgments.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.http import FileResponse
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q, Avg, Case, When, Value, IntegerField
from django.utils import timezone
from django.shortcuts import get_object_or_404
from datetime import timedelta

from .models import (
    PolicyCategory, Policy, PolicyVersion,
    PolicyAcknowledgment, PolicyDistribution, PolicyVersionAuditLog
)
from .document_finalization import DocumentConversionError, finalize_policy_version_pdf
from .serializers import (
    PolicyCategorySerializer, PolicyListSerializer, PolicyDetailSerializer,
    PolicyCreateUpdateSerializer, PolicyVersionListSerializer, PolicyVersionDetailSerializer,
    PolicyAcknowledgmentSerializer, PolicyAcknowledgmentCreateSerializer,
    PolicyDistributionSerializer, PolicySummarySerializer, PolicyVersionAuditLogSerializer
)
from .filters import PolicyFilter, PolicyVersionFilter, PolicyAcknowledgmentFilter


class PolicyCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing policy categories.
    """
    queryset = PolicyCategory.objects.all()
    serializer_class = PolicyCategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    @action(detail=True, methods=['get'])
    def policies(self, request, pk=None):
        """Get all policies in this category."""
        category = self.get_object()
        policies = Policy.objects.filter(category=category).select_related(
            'category', 'owner', 'approver'
        ).prefetch_related('versions')

        page = self.paginate_queryset(policies)
        if page is not None:
            serializer = PolicyListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = PolicyListSerializer(policies, many=True)
        return Response(serializer.data)


class PolicyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing policies with versioning support.
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PolicyFilter
    search_fields = ['title', 'policy_code', 'category__name']
    ordering_fields = ['title', 'policy_code', 'status', 'created_at', 'next_review_date']
    ordering = ['-created_at']

    def get_queryset(self):
        return Policy.objects.select_related(
            'category', 'owner', 'approver', 'created_by'
        ).prefetch_related(
            'versions__created_by',
            'versions__approved_by'
        ).all()

    def get_serializer_class(self):
        if self.action == 'list':
            return PolicyListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return PolicyCreateUpdateSerializer
        else:
            return PolicyDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get policy repository summary statistics."""
        policies = self.get_queryset()

        # Basic counts
        total_policies = policies.count()
        active_policies = policies.filter(status='approved').count()
        draft_policies = policies.filter(status='draft').count()

        # Policies due for review
        policies_due_review = policies.filter(
            next_review_date__lte=timezone.now().date()
        ).count()

        # Version and acknowledgment stats
        total_versions = PolicyVersion.objects.count()
        total_acknowledgments = PolicyAcknowledgment.objects.count()

        # Calculate acknowledgment rate
        current_versions = PolicyVersion.objects.filter(is_active=True)
        total_distributions = PolicyDistribution.objects.filter(
            policy_version__in=current_versions
        ).count()
        acknowledgment_rate = (
            (total_acknowledgments / total_distributions * 100)
            if total_distributions > 0 else 0.0
        )

        # Categories count
        categories_count = PolicyCategory.objects.count()

        # Recent activities (last 30 days)
        recent_date = timezone.now() - timedelta(days=30)
        recent_activities = []

        # Recent policies
        recent_policies = policies.filter(created_at__gte=recent_date)[:5]
        for policy in recent_policies:
            recent_activities.append({
                'type': 'policy_created',
                'title': f"Policy created: {policy.title}",
                'date': policy.created_at,
                'policy_id': str(policy.id)
            })

        # Recent versions
        recent_versions = PolicyVersion.objects.filter(
            created_at__gte=recent_date
        ).select_related('policy')[:5]
        for version in recent_versions:
            recent_activities.append({
                'type': 'version_created',
                'title': f"New version {version.version_number} of {version.policy.title}",
                'date': version.created_at,
                'policy_id': str(version.policy.id),
                'version_id': str(version.id)
            })

        # Sort recent activities by date
        recent_activities.sort(key=lambda x: x['date'], reverse=True)
        recent_activities = recent_activities[:10]

        data = {
            'total_policies': total_policies,
            'active_policies': active_policies,
            'draft_policies': draft_policies,
            'policies_due_review': policies_due_review,
            'total_versions': total_versions,
            'total_acknowledgments': total_acknowledgments,
            'acknowledgment_rate': round(acknowledgment_rate, 2),
            'categories_count': categories_count,
            'recent_activities': recent_activities
        }

        serializer = PolicySummarySerializer(data)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """Get all versions of a specific policy."""
        policy = self.get_object()
        versions = policy.versions.select_related(
            'created_by', 'approved_by'
        ).all()

        serializer = PolicyVersionListSerializer(versions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Acknowledge the current version of a policy."""
        policy = self.get_object()
        current_version = policy.current_version

        if not current_version:
            return Response(
                {'error': 'No active version available for acknowledgment'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if already acknowledged
        existing = PolicyAcknowledgment.objects.filter(
            user=request.user,
            policy_version=current_version
        ).first()

        if existing and existing.is_valid:
            return Response(
                {'error': 'Policy already acknowledged'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create acknowledgment
        serializer = PolicyAcknowledgmentCreateSerializer(
            data={'policy_version': current_version.id},
            context={'request': request}
        )

        if serializer.is_valid():
            acknowledgment = serializer.save()

            # Update distribution if exists
            distribution = PolicyDistribution.objects.filter(
                policy_version=current_version,
                distributed_to=request.user
            ).first()

            if distribution:
                distribution.acknowledged = True
                distribution.acknowledged_at = timezone.now()
                distribution.save()

            return Response(
                PolicyAcknowledgmentSerializer(acknowledgment).data,
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def distribute(self, request, pk=None):
        """Distribute policy to users."""
        policy = self.get_object()
        current_version = policy.current_version

        if not current_version or not current_version.is_published:
            return Response(
                {'error': 'No published version available for distribution'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_ids = request.data.get('user_ids', [])
        if not user_ids:
            return Response(
                {'error': 'user_ids required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.filter(id__in=user_ids)

        distributions_created = []
        for user in users:
            distribution, created = PolicyDistribution.objects.get_or_create(
                policy_version=current_version,
                distributed_to=user,
                defaults={
                    'distributed_by': request.user,
                    'notification_sent': False
                }
            )

            if created:
                distributions_created.append(distribution)

        serializer = PolicyDistributionSerializer(distributions_created, many=True)
        return Response({
            'message': f'Policy distributed to {len(distributions_created)} users',
            'distributions': serializer.data
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def acknowledgment_dashboard(self, request):
        """Get acknowledgment dashboard data for all policies."""
        policies = self.get_queryset().select_related('category').prefetch_related(
            'versions__acknowledgments',
            'versions__distributions'
        )

        dashboard_data = []
        for policy in policies:
            current_version = policy.current_version
            if not current_version:
                continue

            # Get distribution and acknowledgment stats
            distributions = PolicyDistribution.objects.filter(policy_version=current_version)
            acknowledgments = PolicyAcknowledgment.objects.filter(policy_version=current_version)

            total_distributed = distributions.count()
            total_acknowledged = acknowledgments.count()
            acknowledgment_rate = (
                (total_acknowledged / total_distributed * 100)
                if total_distributed > 0 else 0.0
            )

            # Get pending acknowledgments
            pending_users = distributions.filter(acknowledged=False).select_related('distributed_to')

            # Get overdue acknowledgments (>30 days)
            overdue_date = timezone.now() - timedelta(days=30)
            overdue_count = distributions.filter(
                acknowledged=False,
                distributed_at__lte=overdue_date
            ).count()

            dashboard_data.append({
                'policy': {
                    'id': str(policy.id),
                    'title': policy.title,
                    'policy_code': policy.policy_code,
                    'category': policy.category.name if policy.category else None,
                    'status': policy.status
                },
                'current_version': {
                    'id': str(current_version.id),
                    'version_number': current_version.version_number,
                    'effective_date': current_version.effective_date
                },
                'stats': {
                    'total_distributed': total_distributed,
                    'total_acknowledged': total_acknowledged,
                    'acknowledgment_rate': round(acknowledgment_rate, 1),
                    'pending_count': total_distributed - total_acknowledged,
                    'overdue_count': overdue_count
                },
                'pending_users': [
                    {
                        'id': str(dist.distributed_to.id),
                        'email': dist.distributed_to.email,
                        'first_name': getattr(dist.distributed_to, 'first_name', ''),
                        'last_name': getattr(dist.distributed_to, 'last_name', ''),
                        'distributed_at': dist.distributed_at,
                        'reminder_count': dist.reminder_count
                    }
                    for dist in pending_users[:10]  # Limit to first 10 pending users
                ]
            })

        # Sort by acknowledgment rate (lowest first) to show policies needing attention
        dashboard_data.sort(key=lambda x: x['stats']['acknowledgment_rate'])

        return Response(dashboard_data)

    @action(detail=True, methods=['get'])
    def acknowledgment_status(self, request, pk=None):
        """Get detailed acknowledgment status for a specific policy."""
        policy = self.get_object()
        current_version = policy.current_version

        if not current_version:
            return Response(
                {'error': 'No active version available'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get all distributions for current version
        distributions = PolicyDistribution.objects.filter(
            policy_version=current_version
        ).select_related('distributed_to').order_by('-distributed_at')

        # Get all acknowledgments for current version
        acknowledgments = PolicyAcknowledgment.objects.filter(
            policy_version=current_version
        ).select_related('user').order_by('-acknowledged_at')

        # Calculate stats
        total_distributed = distributions.count()
        total_acknowledged = acknowledgments.count()
        acknowledgment_rate = (
            (total_acknowledged / total_distributed * 100)
            if total_distributed > 0 else 0.0
        )

        # Group by status
        acknowledged_users = []
        pending_users = []
        overdue_users = []

        overdue_date = timezone.now() - timedelta(days=30)

        for dist in distributions:
            user_data = {
                'id': str(dist.distributed_to.id),
                'email': dist.distributed_to.email,
                'first_name': getattr(dist.distributed_to, 'first_name', ''),
                'last_name': getattr(dist.distributed_to, 'last_name', ''),
                'distributed_at': dist.distributed_at,
                'reminder_count': dist.reminder_count,
                'last_reminder_sent': dist.last_reminder_sent
            }

            if dist.acknowledged:
                # Find the acknowledgment
                ack = acknowledgments.filter(user=dist.distributed_to).first()
                user_data['acknowledged_at'] = ack.acknowledged_at if ack else None
                acknowledged_users.append(user_data)
            elif dist.distributed_at <= overdue_date:
                overdue_users.append(user_data)
            else:
                pending_users.append(user_data)

        return Response({
            'policy': {
                'id': str(policy.id),
                'title': policy.title,
                'policy_code': policy.policy_code,
                'category': policy.category.name if policy.category else None
            },
            'current_version': {
                'id': str(current_version.id),
                'version_number': current_version.version_number,
                'effective_date': current_version.effective_date
            },
            'stats': {
                'total_distributed': total_distributed,
                'total_acknowledged': total_acknowledged,
                'acknowledgment_rate': round(acknowledgment_rate, 1),
                'pending_count': len(pending_users),
                'overdue_count': len(overdue_users)
            },
            'users': {
                'acknowledged': acknowledged_users,
                'pending': pending_users,
                'overdue': overdue_users
            }
        })

    @action(detail=False, methods=['get'])
    def my_policies(self, request):
        """Get policies requiring acknowledgment by the current user."""
        # Get policies distributed to the current user that haven't been acknowledged
        distributions = PolicyDistribution.objects.filter(
            distributed_to=request.user,
            acknowledged=False
        ).select_related(
            'policy_version__policy__category'
        ).order_by('-distributed_at')

        policies_data = []
        for dist in distributions:
            policy = dist.policy_version.policy
            version = dist.policy_version

            # Check if overdue
            overdue_date = timezone.now() - timedelta(days=30)
            is_overdue = dist.distributed_at <= overdue_date

            policies_data.append({
                'distribution_id': str(dist.id),
                'policy': {
                    'id': str(policy.id),
                    'title': policy.title,
                    'policy_code': policy.policy_code,
                    'category': policy.category.name if policy.category else None,
                    'policy_type': policy.get_policy_type_display()
                },
                'version': {
                    'id': str(version.id),
                    'version_number': version.version_number,
                    'effective_date': version.effective_date,
                    'summary': version.summary,
                    'document': version.document.url if version.document else None
                },
                'distribution': {
                    'distributed_at': dist.distributed_at,
                    'reminder_count': dist.reminder_count,
                    'last_reminder_sent': dist.last_reminder_sent,
                    'is_overdue': is_overdue
                }
            })

        return Response({
            'count': len(policies_data),
            'policies': policies_data
        })


class PolicyVersionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing policy versions.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PolicyVersionFilter
    search_fields = ['version_number', 'summary', 'policy__title']
    ordering_fields = ['version_number', 'created_at', 'effective_date']
    ordering = ['-created_at']

    def get_queryset(self):
        return PolicyVersion.objects.select_related(
            'policy__category', 'created_by', 'approved_by'
        ).prefetch_related(
            'acknowledgments'
        ).all()

    def get_serializer_class(self):
        if self.action == 'list':
            return PolicyVersionListSerializer
        else:
            return PolicyVersionDetailSerializer

    def perform_create(self, serializer):
        version = serializer.save(created_by=self.request.user)
        PolicyVersionAuditLog.objects.create(
            policy_version=version,
            action='uploaded',
            actor=self.request.user,
            details={'filename': version.file_name, 'lifecycle_state': version.lifecycle_state},
        )

    def perform_update(self, serializer):
        version = serializer.save()
        if self.request.FILES.get('document') and version.lifecycle_state != 'final':
            version.lifecycle_state = 'client_modified'
            version.save(update_fields=['lifecycle_state'])
        PolicyVersionAuditLog.objects.create(
            policy_version=version,
            action='edited',
            actor=self.request.user,
            details={'filename': version.file_name, 'lifecycle_state': version.lifecycle_state},
        )

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate this version as the current version."""
        version = self.get_object()

        if not version.is_published:
            return Response(
                {'error': 'Version must be published before activation'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Deactivate other versions
        PolicyVersion.objects.filter(
            policy=version.policy,
            is_active=True
        ).update(is_active=False)

        # Activate this version
        version.is_active = True
        version.save()

        serializer = self.get_serializer(version)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish this version."""
        version = self.get_object()
        version.is_published = True
        version.save()

        serializer = self.get_serializer(version)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve this version."""
        version = self.get_object()
        version.approved_at = timezone.now()
        version.approved_by = request.user
        version.lifecycle_state = 'approved'
        version.save()
        PolicyVersionAuditLog.objects.create(
            policy_version=version,
            action='approved',
            actor=request.user,
            details={'approved_at': version.approved_at.isoformat()},
        )

        # Also update policy status if it's currently draft
        if version.policy.status == 'draft':
            version.policy.status = 'approved'
            version.policy.approver = request.user
            version.policy.save()

        serializer = self.get_serializer(version)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download policy document."""
        version = self.get_object()

        if version.lifecycle_state == 'final':
            if not version.final_pdf:
                return Response(
                    {'error': 'Final PDF is not available'},
                    status=status.HTTP_409_CONFLICT
                )
            PolicyVersionAuditLog.objects.create(
                policy_version=version,
                action='downloaded_pdf',
                actor=request.user,
                details={'filename': version.final_pdf.name},
            )
            return FileResponse(
                version.final_pdf.open('rb'),
                as_attachment=True,
                filename=f"{version.policy.policy_code}_v{version.version_number}.pdf"
            )

        if not _can_download_source(request.user, version):
            return Response(
                {'error': 'This policy version is not finalised for PDF download.'},
                status=status.HTTP_403_FORBIDDEN
            )

        return _source_file_response(version, request.user)

    @action(detail=True, methods=['get'], url_path='download-source')
    def download_source(self, request, pk=None):
        """Download editable source document for authorised editors and administrators."""
        version = self.get_object()
        if not _can_download_source(request.user, version):
            return Response(
                {'error': 'Only authorised editors and administrators can download source documents.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return _source_file_response(version, request.user)

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        """Generate final PDF and lock normal downloads to PDF."""
        version = self.get_object()
        if not _can_download_source(request.user, version):
            return Response(
                {'error': 'Only authorised editors and administrators can finalise documents.'},
                status=status.HTTP_403_FORBIDDEN
            )
        if not version.approved_at:
            return Response(
                {'error': 'Version must be approved before finalisation.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            finalize_policy_version_pdf(version)
        except DocumentConversionError as exc:
            PolicyVersionAuditLog.objects.create(
                policy_version=version,
                action='conversion_failed',
                actor=request.user,
                details={'error': str(exc)},
            )
            return Response({'error': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        version.lifecycle_state = 'final'
        version.finalized_at = timezone.now()
        version.finalized_by = request.user
        version.is_published = True
        version.save(update_fields=[
            'final_pdf', 'final_pdf_size', 'lifecycle_state',
            'finalized_at', 'finalized_by', 'is_published',
        ])
        PolicyVersionAuditLog.objects.create(
            policy_version=version,
            action='finalized',
            actor=request.user,
            details={'final_pdf': version.final_pdf.name},
        )
        serializer = self.get_serializer(version)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='audit-logs')
    def audit_logs(self, request, pk=None):
        """Return audit events for a policy version."""
        version = self.get_object()
        if not _can_download_source(request.user, version):
            return Response({'error': 'Not authorised'}, status=status.HTTP_403_FORBIDDEN)
        serializer = PolicyVersionAuditLogSerializer(
            version.audit_logs.select_related('actor'),
            many=True,
        )
        return Response(serializer.data)


def _source_file_response(version, user):
    if not version.document:
        return Response(
            {'error': 'No document available'},
            status=status.HTTP_404_NOT_FOUND
        )

    PolicyVersionAuditLog.objects.create(
        policy_version=version,
        action='downloaded_source',
        actor=user,
        details={'filename': version.file_name},
    )
    return FileResponse(
        version.document.open('rb'),
        as_attachment=True,
        filename=version.file_name or f"{version.policy.policy_code}_v{version.version_number}{version.file_extension or ''}"
    )


def _can_download_source(user, version):
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    return user.id in {
        version.created_by_id,
        version.policy.owner_id,
        version.policy.approver_id,
    }


class PolicyAcknowledgmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing policy acknowledgments.
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = PolicyAcknowledgmentFilter
    search_fields = ['user__email', 'policy_version__policy__title']
    ordering_fields = ['acknowledged_at']
    ordering = ['-acknowledged_at']

    def get_queryset(self):
        return PolicyAcknowledgment.objects.select_related(
            'user', 'policy_version__policy__category'
        ).all()

    def get_serializer_class(self):
        return PolicyAcknowledgmentSerializer

    @action(detail=False, methods=['get'])
    def my_acknowledgments(self, request):
        """Get current user's acknowledgments."""
        acknowledgments = self.get_queryset().filter(user=request.user)

        page = self.paginate_queryset(acknowledgments)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(acknowledgments, many=True)
        return Response(serializer.data)


class PolicyDistributionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing policy distributions.
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    search_fields = ['distributed_to__email', 'policy_version__policy__title']
    ordering_fields = ['distributed_at', 'acknowledged_at']
    ordering = ['-distributed_at']

    def get_queryset(self):
        return PolicyDistribution.objects.select_related(
            'policy_version__policy__category',
            'distributed_to',
            'distributed_by'
        ).all()

    def get_serializer_class(self):
        return PolicyDistributionSerializer

    @action(detail=False, methods=['get'])
    def my_distributions(self, request):
        """Get policies distributed to current user."""
        distributions = self.get_queryset().filter(distributed_to=request.user)

        page = self.paginate_queryset(distributions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(distributions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending acknowledgments (policies distributed but not acknowledged)."""
        distributions = self.get_queryset().filter(
            distributed_to=request.user,
            acknowledged=False
        )

        page = self.paginate_queryset(distributions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(distributions, many=True)
        return Response(serializer.data)
