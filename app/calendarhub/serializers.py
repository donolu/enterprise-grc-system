from rest_framework import serializers

from .models import CalendarAuditLog, CalendarEvent, CalendarNotificationPreference, CalendarReminderLog


class CalendarOwnerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    name = serializers.CharField()


class CalendarSourceEventSerializer(serializers.Serializer):
    source_type = serializers.CharField()
    source_id = serializers.CharField()
    title = serializers.CharField()
    due_date = serializers.DateField()
    owner = CalendarOwnerSerializer(allow_null=True)
    source_url = serializers.CharField()
    status = serializers.CharField()
    module = serializers.CharField()
    metadata = serializers.DictField()
    days_until_due = serializers.IntegerField()
    is_overdue = serializers.BooleanField()


class CalendarEventSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source='owner.email', read_only=True)

    class Meta:
        model = CalendarEvent
        fields = [
            'id', 'title', 'description', 'event_type', 'due_date', 'owner',
            'owner_email', 'status', 'source_url', 'metadata', 'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CalendarNotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarNotificationPreference
        fields = [
            'email_enabled', 'advance_reminder_days', 'due_date_enabled',
            'overdue_enabled', 'updated_at',
        ]
        read_only_fields = ['updated_at']


class CalendarReminderLogSerializer(serializers.ModelSerializer):
    recipient_email = serializers.EmailField(source='recipient.email', read_only=True)

    class Meta:
        model = CalendarReminderLog
        fields = [
            'id', 'source_type', 'source_id', 'title', 'due_date', 'recipient',
            'recipient_email', 'reminder_type', 'sent_at', 'email_sent', 'metadata',
        ]
        read_only_fields = fields


class CalendarAuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source='actor.email', read_only=True)

    class Meta:
        model = CalendarAuditLog
        fields = [
            'id', 'action', 'event', 'source_type', 'source_id', 'actor',
            'actor_email', 'details', 'created_at',
        ]
        read_only_fields = fields
