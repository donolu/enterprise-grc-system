from django.utils.dateparse import parse_date
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import CalendarAuditLog, CalendarEvent, CalendarNotificationPreference, CalendarReminderLog
from .serializers import (
    CalendarAuditLogSerializer,
    CalendarEventSerializer,
    CalendarNotificationPreferenceSerializer,
    CalendarReminderLogSerializer,
    CalendarSourceEventSerializer,
)
from .services import list_calendar_events


class CalendarEventViewSet(viewsets.ModelViewSet):
    serializer_class = CalendarEventSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['event_type', 'status', 'owner']
    search_fields = ['title', 'description']
    ordering_fields = ['due_date', 'title', 'created_at']
    ordering = ['due_date', 'title']

    def get_queryset(self):
        return CalendarEvent.objects.select_related('owner', 'created_by')

    def perform_create(self, serializer):
        event = serializer.save(created_by=self.request.user)
        CalendarAuditLog.objects.create(
            action='created',
            event=event,
            actor=self.request.user,
            details={'title': event.title, 'due_date': event.due_date.isoformat()},
        )

    def perform_update(self, serializer):
        event = serializer.save()
        CalendarAuditLog.objects.create(
            action='updated',
            event=event,
            actor=self.request.user,
            details={'title': event.title, 'due_date': event.due_date.isoformat()},
        )

    def perform_destroy(self, instance):
        CalendarAuditLog.objects.create(
            action='deleted',
            event=instance,
            actor=self.request.user,
            details={'title': instance.title, 'due_date': instance.due_date.isoformat()},
        )
        instance.delete()

    @action(detail=False, methods=['get'], url_path='combined')
    def combined(self, request):
        start_date = _parse_date_param(request, 'start')
        end_date = _parse_date_param(request, 'end')
        owner = request.user if request.query_params.get('owner') == 'me' else None
        module = request.query_params.get('module')

        events = [event.to_dict() for event in list_calendar_events(start_date, end_date, owner)]
        if module:
            events = [event for event in events if event['module'] == module]
        serializer = CalendarSourceEventSerializer(events, many=True)
        return Response(serializer.data)


class CalendarNotificationPreferenceViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        preference, _ = CalendarNotificationPreference.objects.get_or_create(user=request.user)
        serializer = CalendarNotificationPreferenceSerializer(preference)
        return Response(serializer.data)

    def create(self, request):
        preference, _ = CalendarNotificationPreference.objects.get_or_create(user=request.user)
        serializer = CalendarNotificationPreferenceSerializer(preference, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class CalendarReminderLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CalendarReminderLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['source_type', 'recipient', 'reminder_type', 'email_sent']
    ordering_fields = ['sent_at', 'due_date']
    ordering = ['-sent_at']

    def get_queryset(self):
        return CalendarReminderLog.objects.select_related('recipient')


class CalendarAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CalendarAuditLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['action', 'source_type', 'actor']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return CalendarAuditLog.objects.select_related('event', 'actor')


def _parse_date_param(request, key):
    value = request.query_params.get(key)
    if not value:
        return None
    parsed = parse_date(value)
    if parsed is None:
        raise ValidationError({key: 'Use YYYY-MM-DD.'})
    return parsed
