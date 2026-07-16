import tempfile
from pathlib import Path

from django.core.management.base import CommandError
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from assets.management.commands.import_assets import Command as AssetImportCommand
from .audit import (
    asset_changed_values,
    asset_display,
    audit_asset_change,
    snapshot_asset,
)
from .models import Asset, AssetReviewReminderLog
from .serializers import (
    AssetDetailSerializer,
    AssetImportSummarySerializer,
    AssetListSerializer,
    AssetReviewReminderLogSerializer,
)


class AssetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class AssetViewSet(viewsets.ModelViewSet):
    """
    CRUD API for information assets.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = AssetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'asset_type', 'classification', 'criticality', 'lifecycle_status',
        'owner', 'location',
    ]
    search_fields = [
        'asset_id', 'name', 'description', 'owner_name', 'serial_number',
        'ip_address', 'mac_address', 'location',
    ]
    ordering_fields = [
        'asset_id', 'name', 'asset_type', 'criticality', 'next_review_date',
        'updated_at',
    ]
    ordering = ['asset_id']

    def get_queryset(self):
        return Asset.objects.select_related('owner', 'created_by').prefetch_related(
            'linked_risks', 'linked_controls', 'linked_documents'
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return AssetListSerializer
        return AssetDetailSerializer

    def perform_create(self, serializer):
        asset = serializer.save()
        audit_asset_change(
            event='ASSET_CREATED',
            actor=self.request.user,
            target=asset,
            object_display=asset_display(asset),
            request=self.request,
            new=snapshot_asset(asset),
        )

    def perform_update(self, serializer):
        previous = snapshot_asset(serializer.instance)
        asset = serializer.save()
        new = snapshot_asset(asset)
        previous_changed, new_changed = asset_changed_values(previous, new)
        if previous_changed or new_changed:
            audit_asset_change(
                event='ASSET_UPDATED',
                actor=self.request.user,
                target=asset,
                object_display=asset_display(asset),
                request=self.request,
                previous=previous_changed,
                new=new_changed,
            )

    def perform_destroy(self, instance):
        previous = snapshot_asset(instance)
        audit_asset_change(
            event='ASSET_DELETED',
            actor=self.request.user,
            target=instance,
            object_display=asset_display(instance),
            request=self.request,
            previous=previous,
        )
        instance.delete()

    @action(detail=False, methods=['get'])
    def due_for_review(self, request):
        """List assets with reviews due today or overdue."""
        from django.utils import timezone
        queryset = self.get_queryset().filter(next_review_date__lte=timezone.now().date())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = AssetListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = AssetListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=['post'],
        parser_classes=[MultiPartParser, FormParser],
        url_path='import-register',
    )
    def import_register(self, request):
        """Import an asset register spreadsheet from the admin web interface."""
        if not request.user.is_staff and not request.user.is_superuser:
            return Response(
                {'detail': 'Only staff administrators can import asset registers.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        upload = request.FILES.get('file')
        if not upload:
            return Response(
                {'file': ['An asset register spreadsheet is required.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not upload.name.lower().endswith('.xlsx'):
            return Response(
                {'file': ['Asset register imports require a .xlsx file.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        dry_run = str(request.data.get('dry_run', '')).lower() in {'1', 'true', 'yes'}
        command = AssetImportCommand()

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            for chunk in upload.chunks():
                temp_file.write(chunk)

        try:
            try:
                entries = command.collect_entries(temp_path, source_label=upload.name)
            except CommandError:
                return Response(
                    {
                        'detail': 'Asset register import failed. Check the spreadsheet format.',
                        'code': 'asset_import_invalid',
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if dry_run:
                serializer = AssetImportSummarySerializer({
                    'dry_run': True,
                    'importable_count': len(entries),
                    'skipped_count': command.skipped_count,
                    'sheets': command.sheet_counts,
                    'samples': [
                        {
                            'asset_id': entry['asset_id'],
                            'name': entry['name'],
                            'asset_type': entry['asset_type'],
                            'source_sheet': entry['source_sheet'],
                        }
                        for entry in entries[:10]
                    ],
                })
                return Response(serializer.data)

            with transaction.atomic():
                imported, updated = command.import_entries(entries, upload.name, request.user)
                command.record_import_audit_event(
                    upload.name,
                    entries,
                    request.user,
                    imported,
                    updated,
                )

            serializer = AssetImportSummarySerializer({
                'dry_run': False,
                'imported_count': imported,
                'updated_count': updated,
                'skipped_count': command.skipped_count,
                'sheets': command.sheet_counts,
            })
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        finally:
            temp_path.unlink(missing_ok=True)


class AssetReviewReminderLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AssetReviewReminderLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['asset', 'owner', 'reminder_type', 'email_sent']
    ordering_fields = ['sent_at', 'review_date']
    ordering = ['-sent_at']

    def get_queryset(self):
        return AssetReviewReminderLog.objects.select_related('asset', 'owner')
