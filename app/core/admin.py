from django.contrib import admin

from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'at', 'object_type', 'object_id')
    list_filter = ('event', 'at')
    search_fields = ('event', 'user__email', 'user__username')
    readonly_fields = ('user', 'event', 'details', 'at')
    date_hierarchy = 'at'
    ordering = ('-at',)

    @admin.display(description='Object type')
    def object_type(self, obj):
        return obj.details.get('object', {}).get('type', '')

    @admin.display(description='Object ID')
    def object_id(self, obj):
        return obj.details.get('object', {}).get('id', '')
