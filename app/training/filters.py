"""
Training Filters

Advanced filtering for training videos and campaigns.
"""

import django_filters
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from .models import TrainingVideo, SecurityAwarenessCampaign, TrainingCategory


class TrainingVideoFilter(django_filters.FilterSet):
    """
    Advanced filtering for training videos.
    """

    # Text search
    search = django_filters.CharFilter(method='filter_search')

    # Category filters
    category = django_filters.UUIDFilter(field_name='category__id')
    category_name = django_filters.CharFilter(
        field_name='category__name',
        lookup_expr='icontains'
    )

    # Content filters
    video_provider = django_filters.MultipleChoiceFilter(
        choices=TrainingVideo.video_provider.field.choices
    )
    difficulty_level = django_filters.MultipleChoiceFilter(
        choices=TrainingVideo.difficulty_level.field.choices
    )

    # Status filters
    is_published = django_filters.BooleanFilter()
    has_duration = django_filters.BooleanFilter(method='filter_has_duration')

    # Duration filters
    duration_min = django_filters.NumberFilter(
        field_name='duration_minutes',
        lookup_expr='gte'
    )
    duration_max = django_filters.NumberFilter(
        field_name='duration_minutes',
        lookup_expr='lte'
    )

    # View count filters
    popular = django_filters.BooleanFilter(method='filter_popular')
    view_count_min = django_filters.NumberFilter(
        field_name='view_count',
        lookup_expr='gte'
    )

    # Date filters
    created_after = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='gte'
    )
    created_before = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='lte'
    )
    published_after = django_filters.DateFilter(
        field_name='published_at',
        lookup_expr='gte'
    )

    # User filters
    created_by = django_filters.UUIDFilter(field_name='created_by__id')

    class Meta:
        model = TrainingVideo
        fields = [
            'category', 'video_provider', 'difficulty_level', 'is_published'
        ]

    def filter_search(self, queryset, name, value):
        """Search across multiple fields."""
        if not value:
            return queryset

        return queryset.filter(
            Q(title__icontains=value) |
            Q(description__icontains=value) |
            Q(category__name__icontains=value)
        )

    def filter_has_duration(self, queryset, name, value):
        """Filter videos with/without duration specified."""
        if value:
            return queryset.filter(duration_minutes__isnull=False)
        else:
            return queryset.filter(duration_minutes__isnull=True)

    def filter_popular(self, queryset, name, value):
        """Filter popular videos (top 25% by view count)."""
        if value:
            # Calculate threshold for top 25% of videos by view count
            from django.db.models import Percentile
            threshold = queryset.aggregate(
                threshold=Percentile('view_count', 0.75)
            )['threshold'] or 0
            return queryset.filter(view_count__gte=threshold)
        return queryset


class CampaignFilter(django_filters.FilterSet):
    """
    Advanced filtering for security awareness campaigns.
    """

    # Text search
    search = django_filters.CharFilter(method='filter_search')

    # Status filters
    is_active = django_filters.BooleanFilter()
    status = django_filters.ChoiceFilter(
        method='filter_status',
        choices=[
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('scheduled', 'Scheduled'),
            ('ended', 'Ended'),
            ('ready_to_send', 'Ready to Send')
        ]
    )

    # Frequency filters
    send_frequency = django_filters.MultipleChoiceFilter(
        choices=SecurityAwarenessCampaign.send_frequency.field.choices
    )

    # Target audience filters
    send_to_all_users = django_filters.BooleanFilter()
    has_target_users = django_filters.BooleanFilter(method='filter_has_target_users')

    # Date filters
    start_date_after = django_filters.DateFilter(
        field_name='start_date',
        lookup_expr='gte'
    )
    start_date_before = django_filters.DateFilter(
        field_name='start_date',
        lookup_expr='lte'
    )
    end_date_after = django_filters.DateFilter(
        field_name='end_date',
        lookup_expr='gte'
    )
    end_date_before = django_filters.DateFilter(
        field_name='end_date',
        lookup_expr='lte'
    )

    # Performance filters
    high_open_rate = django_filters.BooleanFilter(method='filter_high_open_rate')
    low_open_rate = django_filters.BooleanFilter(method='filter_low_open_rate')
    has_sends = django_filters.BooleanFilter(method='filter_has_sends')

    # Scheduling filters
    due_to_send = django_filters.BooleanFilter(method='filter_due_to_send')
    overdue = django_filters.BooleanFilter(method='filter_overdue')

    # User filters
    created_by = django_filters.UUIDFilter(field_name='created_by__id')

    class Meta:
        model = SecurityAwarenessCampaign
        fields = [
            'is_active', 'send_frequency', 'send_to_all_users', 'created_by'
        ]

    def filter_search(self, queryset, name, value):
        """Search across multiple fields."""
        if not value:
            return queryset

        return queryset.filter(
            Q(name__icontains=value) |
            Q(description__icontains=value) |
            Q(subject_line__icontains=value)
        )

    def filter_status(self, queryset, name, value):
        """Filter by campaign status."""
        now = timezone.now()

        if value == 'active':
            return queryset.filter(
                is_active=True,
                start_date__lte=now
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gt=now)
            )
        elif value == 'inactive':
            return queryset.filter(is_active=False)
        elif value == 'scheduled':
            return queryset.filter(
                is_active=True,
                start_date__gt=now
            )
        elif value == 'ended':
            return queryset.filter(
                end_date__isnull=False,
                end_date__lte=now
            )
        elif value == 'ready_to_send':
            return queryset.filter(
                is_active=True,
                next_send_date__lte=now
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gt=now)
            )

        return queryset

    def filter_has_target_users(self, queryset, name, value):
        """Filter campaigns with specific target users."""
        if value:
            return queryset.filter(
                send_to_all_users=False,
                target_users__isnull=False
            ).distinct()
        else:
            return queryset.filter(
                Q(send_to_all_users=True) |
                Q(target_users__isnull=True)
            )

    def filter_high_open_rate(self, queryset, name, value):
        """Filter campaigns with high open rates (>30%)."""
        if value:
            return queryset.filter(
                total_sent__gt=0
            ).extra(
                where=["(total_opened::float / total_sent::float) * 100 > 30"]
            )
        return queryset

    def filter_low_open_rate(self, queryset, name, value):
        """Filter campaigns with low open rates (<10%)."""
        if value:
            return queryset.filter(
                total_sent__gt=0
            ).extra(
                where=["(total_opened::float / total_sent::float) * 100 < 10"]
            )
        return queryset

    def filter_has_sends(self, queryset, name, value):
        """Filter campaigns that have sent emails."""
        if value:
            return queryset.filter(total_sent__gt=0)
        else:
            return queryset.filter(total_sent=0)

    def filter_due_to_send(self, queryset, name, value):
        """Filter campaigns due to send."""
        if value:
            return queryset.filter(
                is_active=True,
                next_send_date__lte=timezone.now()
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gt=timezone.now())
            )
        return queryset

    def filter_overdue(self, queryset, name, value):
        """Filter campaigns that are overdue (due date passed by >24 hours)."""
        if value:
            overdue_threshold = timezone.now() - timedelta(hours=24)
            return queryset.filter(
                is_active=True,
                next_send_date__lt=overdue_threshold
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gt=timezone.now())
            )
        return queryset