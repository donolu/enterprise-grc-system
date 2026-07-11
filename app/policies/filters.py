"""
Policy Repository Filters

Advanced filtering capabilities for policies, versions, and acknowledgments.
"""

import django_filters
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from .models import Policy, PolicyVersion, PolicyAcknowledgment, PolicyDistribution


class PolicyFilter(django_filters.FilterSet):
    """
    Advanced filtering for policies.
    """

    # Text search
    search = django_filters.CharFilter(method='filter_search')

    # Status filters
    status = django_filters.MultipleChoiceFilter(
        choices=Policy.APPROVAL_STATUS_CHOICES
    )
    policy_type = django_filters.MultipleChoiceFilter(
        choices=Policy.POLICY_TYPE_CHOICES
    )

    # Category filters
    category = django_filters.UUIDFilter(field_name='category__id')
    category_name = django_filters.CharFilter(
        field_name='category__name',
        lookup_expr='icontains'
    )

    # Ownership filters
    owner = django_filters.UUIDFilter(field_name='owner__id')
    created_by = django_filters.UUIDFilter(field_name='created_by__id')

    # Date filters
    created_after = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='gte'
    )
    created_before = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='lte'
    )

    # Review filters
    due_for_review = django_filters.BooleanFilter(method='filter_due_for_review')
    review_overdue = django_filters.BooleanFilter(method='filter_review_overdue')

    # Acknowledgment filters
    requires_acknowledgment = django_filters.BooleanFilter()
    has_active_version = django_filters.BooleanFilter(method='filter_has_active_version')

    class Meta:
        model = Policy
        fields = [
            'status', 'policy_type', 'category', 'owner', 'created_by',
            'requires_acknowledgment'
        ]

    def filter_search(self, queryset, name, value):
        """Search across multiple fields."""
        if not value:
            return queryset

        return queryset.filter(
            Q(title__icontains=value) |
            Q(policy_code__icontains=value) |
            Q(category__name__icontains=value)
        )

    def filter_due_for_review(self, queryset, name, value):
        """Filter policies due for review."""
        if value:
            return queryset.filter(
                next_review_date__lte=timezone.now().date()
            )
        return queryset

    def filter_review_overdue(self, queryset, name, value):
        """Filter policies with overdue reviews."""
        if value:
            overdue_date = timezone.now().date() - timedelta(days=30)
            return queryset.filter(
                next_review_date__lte=overdue_date
            )
        return queryset

    def filter_has_active_version(self, queryset, name, value):
        """Filter policies with/without active versions."""
        if value:
            return queryset.filter(versions__is_active=True)
        else:
            return queryset.exclude(versions__is_active=True)


class PolicyVersionFilter(django_filters.FilterSet):
    """
    Advanced filtering for policy versions.
    """

    # Policy filters
    policy = django_filters.UUIDFilter(field_name='policy__id')
    policy_code = django_filters.CharFilter(
        field_name='policy__policy_code',
        lookup_expr='icontains'
    )
    policy_title = django_filters.CharFilter(
        field_name='policy__title',
        lookup_expr='icontains'
    )

    # Version status filters
    is_active = django_filters.BooleanFilter()
    is_published = django_filters.BooleanFilter()
    is_approved = django_filters.BooleanFilter(method='filter_is_approved')

    # Date filters
    created_after = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='gte'
    )
    created_before = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='lte'
    )
    effective_after = django_filters.DateFilter(
        field_name='effective_date',
        lookup_expr='gte'
    )
    effective_before = django_filters.DateFilter(
        field_name='effective_date',
        lookup_expr='lte'
    )

    # Content filters
    version_number = django_filters.CharFilter(lookup_expr='icontains')
    has_document = django_filters.BooleanFilter(method='filter_has_document')

    # User filters
    created_by = django_filters.UUIDFilter(field_name='created_by__id')
    approved_by = django_filters.UUIDFilter(field_name='approved_by__id')

    class Meta:
        model = PolicyVersion
        fields = [
            'policy', 'is_active', 'is_published', 'version_number'
        ]

    def filter_is_approved(self, queryset, name, value):
        """Filter approved versions."""
        if value:
            return queryset.filter(approved_at__isnull=False)
        else:
            return queryset.filter(approved_at__isnull=True)

    def filter_has_document(self, queryset, name, value):
        """Filter versions with/without documents."""
        if value:
            return queryset.exclude(document='')
        else:
            return queryset.filter(document='')


class PolicyAcknowledgmentFilter(django_filters.FilterSet):
    """
    Advanced filtering for policy acknowledgments.
    """

    # User filters
    user = django_filters.UUIDFilter(field_name='user__id')
    user_email = django_filters.CharFilter(
        field_name='user__email',
        lookup_expr='icontains'
    )

    # Policy filters
    policy = django_filters.UUIDFilter(field_name='policy_version__policy__id')
    policy_code = django_filters.CharFilter(
        field_name='policy_version__policy__policy_code',
        lookup_expr='icontains'
    )
    policy_version = django_filters.UUIDFilter(field_name='policy_version__id')

    # Date filters
    acknowledged_after = django_filters.DateTimeFilter(
        field_name='acknowledged_at',
        lookup_expr='gte'
    )
    acknowledged_before = django_filters.DateTimeFilter(
        field_name='acknowledged_at',
        lookup_expr='lte'
    )

    # Validity filters
    is_expired = django_filters.BooleanFilter(method='filter_is_expired')
    expires_soon = django_filters.NumberFilter(method='filter_expires_soon')

    class Meta:
        model = PolicyAcknowledgment
        fields = ['user', 'policy_version']

    def filter_is_expired(self, queryset, name, value):
        """Filter expired acknowledgments."""
        if value:
            return queryset.filter(expires_at__lt=timezone.now())
        else:
            return queryset.filter(
                Q(expires_at__isnull=True) |
                Q(expires_at__gte=timezone.now())
            )

    def filter_expires_soon(self, queryset, name, value):
        """Filter acknowledgments expiring within N days."""
        if value:
            expire_date = timezone.now() + timedelta(days=value)
            return queryset.filter(
                expires_at__lte=expire_date,
                expires_at__gte=timezone.now()
            )
        return queryset


class PolicyDistributionFilter(django_filters.FilterSet):
    """
    Advanced filtering for policy distributions.
    """

    # User filters
    distributed_to = django_filters.UUIDFilter(field_name='distributed_to__id')
    distributed_by = django_filters.UUIDFilter(field_name='distributed_by__id')
    user_email = django_filters.CharFilter(
        field_name='distributed_to__email',
        lookup_expr='icontains'
    )

    # Policy filters
    policy = django_filters.UUIDFilter(field_name='policy_version__policy__id')
    policy_code = django_filters.CharFilter(
        field_name='policy_version__policy__policy_code',
        lookup_expr='icontains'
    )
    policy_version = django_filters.UUIDFilter(field_name='policy_version__id')

    # Status filters
    acknowledged = django_filters.BooleanFilter()
    notification_sent = django_filters.BooleanFilter()
    is_overdue = django_filters.BooleanFilter(method='filter_is_overdue')

    # Date filters
    distributed_after = django_filters.DateTimeFilter(
        field_name='distributed_at',
        lookup_expr='gte'
    )
    distributed_before = django_filters.DateTimeFilter(
        field_name='distributed_at',
        lookup_expr='lte'
    )

    # Reminder filters
    needs_reminder = django_filters.BooleanFilter(method='filter_needs_reminder')
    reminder_count_gte = django_filters.NumberFilter(
        field_name='reminder_count',
        lookup_expr='gte'
    )

    class Meta:
        model = PolicyDistribution
        fields = [
            'distributed_to', 'distributed_by', 'policy_version',
            'acknowledged', 'notification_sent'
        ]

    def filter_is_overdue(self, queryset, name, value):
        """Filter overdue distributions."""
        if value:
            overdue_date = timezone.now() - timedelta(days=30)
            return queryset.filter(
                distributed_at__lte=overdue_date,
                acknowledged=False
            )
        return queryset

    def filter_needs_reminder(self, queryset, name, value):
        """Filter distributions that need reminders."""
        if value:
            reminder_date = timezone.now() - timedelta(days=7)
            return queryset.filter(
                Q(last_reminder_sent__isnull=True) |
                Q(last_reminder_sent__lte=reminder_date),
                acknowledged=False
            )
        return queryset