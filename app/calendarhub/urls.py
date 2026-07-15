from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CalendarAuditLogViewSet,
    CalendarEventViewSet,
    CalendarNotificationPreferenceViewSet,
    CalendarReminderLogViewSet,
)

router = DefaultRouter()
router.register(r'events', CalendarEventViewSet, basename='calendar-events')
router.register(r'preferences', CalendarNotificationPreferenceViewSet, basename='calendar-preferences')
router.register(r'reminders', CalendarReminderLogViewSet, basename='calendar-reminders')
router.register(r'audit', CalendarAuditLogViewSet, basename='calendar-audit')

app_name = 'calendarhub'

urlpatterns = [
    path('', include(router.urls)),
]
