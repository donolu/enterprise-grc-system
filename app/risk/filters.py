import django_filters
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Risk, RiskCategory, RiskAction

User = get_user_model()


class RiskFilter(django_filters.FilterSet):
    """
    Advanced filtering for Risk model with multiple criteria support.
    """
    
    # Risk level filtering (supports multiple values)
    risk_level = django_filters.MultipleChoiceFilter(
        field_name='risk_level',
        choices=Risk.RISK_LEVELS,
        help_text='Filter by risk level(s). Supports multiple values.'
    )
    
    # Status filtering (supports multiple values)
    status = django_filters.MultipleChoiceFilter(
        field_name='status',
        choices=Risk.STATUS_CHOICES,
        help_text='Filter by risk status(es). Supports multiple values.'
    )
    
    # Treatment strategy filtering
    treatment_strategy = django_filters.MultipleChoiceFilter(
        field_name='treatment_strategy',
        choices=Risk.TREATMENT_STRATEGIES,
        help_text='Filter by treatment strategy. Supports multiple values.'
    )
    
    # Category filtering
    category = django_filters.ModelMultipleChoiceFilter(
        field_name='category',
        queryset=RiskCategory.objects.all(),
        help_text='Filter by risk category ID(s). Supports multiple values.'
    )
    
    # Risk owner filtering
    risk_owner = django_filters.NumberFilter(
        field_name='risk_owner',
        help_text='Filter by risk owner user ID.'
    )
    
    # Risk score range filtering
    risk_score_min = django_filters.NumberFilter(
        method='filter_risk_score_min',
        help_text='Filter risks with risk score >= this value.'
    )
    
    risk_score_max = django_filters.NumberFilter(
        method='filter_risk_score_max',
        help_text='Filter risks with risk score <= this value.'
    )
    
    # Impact range filtering
    impact_min = django_filters.NumberFilter(
        field_name='impact',
        lookup_expr='gte',
        help_text='Filter risks with impact >= this value (1-5).'
    )
    
    impact_max = django_filters.NumberFilter(
        field_name='impact',
        lookup_expr='lte',
        help_text='Filter risks with impact <= this value (1-5).'
    )
    
    # Likelihood range filtering
    likelihood_min = django_filters.NumberFilter(
        field_name='likelihood',
        lookup_expr='gte',
        help_text='Filter risks with likelihood >= this value (1-5).'
    )
    
    likelihood_max = django_filters.NumberFilter(
        field_name='likelihood',
        lookup_expr='lte',
        help_text='Filter risks with likelihood <= this value (1-5).'
    )
    
    # Date range filtering
    identified_date_after = django_filters.DateFilter(
        field_name='identified_date',
        lookup_expr='gte',
        help_text='Filter risks identified on or after this date (YYYY-MM-DD).'
    )
    
    identified_date_before = django_filters.DateFilter(
        field_name='identified_date',
        lookup_expr='lte',
        help_text='Filter risks identified on or before this date (YYYY-MM-DD).'
    )
    
    last_assessed_after = django_filters.DateFilter(
        field_name='last_assessed_date',
        lookup_expr='gte',
        help_text='Filter risks last assessed on or after this date (YYYY-MM-DD).'
    )
    
    last_assessed_before = django_filters.DateFilter(
        field_name='last_assessed_date',
        lookup_expr='lte',
        help_text='Filter risks last assessed on or before this date (YYYY-MM-DD).'
    )
    
    next_review_after = django_filters.DateFilter(
        field_name='next_review_date',
        lookup_expr='gte',
        help_text='Filter risks with next review on or after this date (YYYY-MM-DD).'
    )
    
    next_review_before = django_filters.DateFilter(
        field_name='next_review_date',
        lookup_expr='lte',
        help_text='Filter risks with next review on or before this date (YYYY-MM-DD).'
    )
    
    # Boolean filters
    overdue_review = django_filters.BooleanFilter(
        method='filter_overdue_review',
        help_text='Filter risks that are overdue for review.'
    )
    
    active_only = django_filters.BooleanFilter(
        method='filter_active_only',
        help_text='Filter only active risks (excludes closed/transferred).'
    )
    
    high_priority = django_filters.BooleanFilter(
        method='filter_high_priority',
        help_text='Filter only high and critical priority risks.'
    )
    
    has_treatment = django_filters.BooleanFilter(
        method='filter_has_treatment',
        help_text='Filter risks that have a treatment strategy defined.'
    )
    
    my_risks = django_filters.BooleanFilter(
        method='filter_my_risks',
        help_text='Filter risks owned by the current user.'
    )
    
    # Text search across multiple fields
    search = django_filters.CharFilter(
        method='filter_search',
        help_text='Search across risk ID, title, and description.'
    )
    
    class Meta:
        model = Risk
        fields = []  # We define custom fields above
    
    def filter_risk_score_min(self, queryset, name, value):
        """Filter by minimum risk score (impact * likelihood)."""
        if value is not None:
            # Use raw SQL for calculated field
            return queryset.extra(
                where=["impact * likelihood >= %s"],
                params=[value]
            )
        return queryset
    
    def filter_risk_score_max(self, queryset, name, value):
        """Filter by maximum risk score (impact * likelihood)."""
        if value is not None:
            # Use raw SQL for calculated field
            return queryset.extra(
                where=["impact * likelihood <= %s"],
                params=[value]
            )
        return queryset
    
    def filter_overdue_review(self, queryset, name, value):
        """Filter risks that are overdue for review."""
        if value:
            today = timezone.now().date()
            return queryset.filter(
                next_review_date__lt=today
            ).exclude(
                next_review_date__isnull=True
            )
        elif value is False:
            today = timezone.now().date()
            return queryset.filter(
                Q(next_review_date__gte=today) | Q(next_review_date__isnull=True)
            )
        return queryset
    
    def filter_active_only(self, queryset, name, value):
        """Filter only active risks."""
        if value:
            return queryset.filter(status__in=[
                'identified', 'assessed', 'treatment_planned',
                'treatment_in_progress', 'mitigated', 'accepted'
            ])
        elif value is False:
            return queryset.filter(status__in=['closed', 'transferred'])
        return queryset
    
    def filter_high_priority(self, queryset, name, value):
        """Filter high and critical priority risks."""
        if value:
            return queryset.filter(risk_level__in=['high', 'critical'])
        elif value is False:
            return queryset.filter(risk_level__in=['low', 'medium'])
        return queryset
    
    def filter_has_treatment(self, queryset, name, value):
        """Filter risks with or without treatment strategies."""
        if value:
            return queryset.exclude(treatment_strategy__isnull=True).exclude(treatment_strategy='')
        elif value is False:
            return queryset.filter(Q(treatment_strategy__isnull=True) | Q(treatment_strategy=''))
        return queryset
    
    def filter_my_risks(self, queryset, name, value):
        """Filter risks owned by the current user."""
        if value and hasattr(self.request, 'user') and self.request.user.is_authenticated:
            return queryset.filter(risk_owner=self.request.user)
        return queryset
    
    def filter_search(self, queryset, name, value):
        """Search across multiple text fields."""
        if value:
            return queryset.filter(
                Q(risk_id__icontains=value) |
                Q(title__icontains=value) |
                Q(description__icontains=value) |
                Q(potential_impact_description__icontains=value) |
                Q(current_controls__icontains=value)
            )
        return queryset


class RiskActionFilter(django_filters.FilterSet):
    """
    Advanced filtering for RiskAction model with multiple criteria support.
    """
    
    # Status filtering (supports multiple values)
    status = django_filters.MultipleChoiceFilter(
        field_name='status',
        choices=RiskAction.STATUS_CHOICES,
        help_text='Filter by action status(es). Supports multiple values.'
    )
    
    # Priority filtering (supports multiple values)
    priority = django_filters.MultipleChoiceFilter(
        field_name='priority',
        choices=RiskAction.PRIORITY_CHOICES,
        help_text='Filter by action priority. Supports multiple values.'
    )
    
    # Action type filtering
    action_type = django_filters.MultipleChoiceFilter(
        field_name='action_type',
        choices=RiskAction.ACTION_TYPES,
        help_text='Filter by action type. Supports multiple values.'
    )
    
    # Risk filtering
    risk = django_filters.ModelMultipleChoiceFilter(
        field_name='risk',
        queryset=Risk.objects.all(),
        help_text='Filter by risk ID(s). Supports multiple values.'
    )
    
    # Risk level filtering (based on related risk)
    risk_level = django_filters.MultipleChoiceFilter(
        field_name='risk__risk_level',
        choices=Risk.RISK_LEVELS,
        help_text='Filter by related risk level. Supports multiple values.'
    )
    
    # Assigned user filtering
    assigned_to = django_filters.ModelMultipleChoiceFilter(
        field_name='assigned_to',
        queryset=User.objects.all(),
        help_text='Filter by assigned user ID(s). Supports multiple values.'
    )
    
    # Progress range filtering
    progress_min = django_filters.NumberFilter(
        field_name='progress_percentage',
        lookup_expr='gte',
        help_text='Filter actions with progress >= this value (0-100).'
    )
    
    progress_max = django_filters.NumberFilter(
        field_name='progress_percentage',
        lookup_expr='lte',
        help_text='Filter actions with progress <= this value (0-100).'
    )
    
    # Date range filtering
    start_date_after = django_filters.DateFilter(
        field_name='start_date',
        lookup_expr='gte',
        help_text='Filter actions with start date on or after this date (YYYY-MM-DD).'
    )
    
    start_date_before = django_filters.DateFilter(
        field_name='start_date',
        lookup_expr='lte',
        help_text='Filter actions with start date on or before this date (YYYY-MM-DD).'
    )
    
    due_date_after = django_filters.DateFilter(
        field_name='due_date',
        lookup_expr='gte',
        help_text='Filter actions due on or after this date (YYYY-MM-DD).'
    )
    
    due_date_before = django_filters.DateFilter(
        field_name='due_date',
        lookup_expr='lte',
        help_text='Filter actions due on or before this date (YYYY-MM-DD).'
    )
    
    completed_date_after = django_filters.DateFilter(
        field_name='completed_date',
        lookup_expr='gte',
        help_text='Filter actions completed on or after this date (YYYY-MM-DD).'
    )
    
    completed_date_before = django_filters.DateFilter(
        field_name='completed_date',
        lookup_expr='lte',
        help_text='Filter actions completed on or before this date (YYYY-MM-DD).'
    )
    
    # Boolean filters
    overdue = django_filters.BooleanFilter(
        method='filter_overdue',
        help_text='Filter actions that are overdue.'
    )
    
    due_soon = django_filters.BooleanFilter(
        method='filter_due_soon',
        help_text='Filter actions due within the next 7 days.'
    )
    
    active_only = django_filters.BooleanFilter(
        method='filter_active_only',
        help_text='Filter only active actions (excludes completed/cancelled).'
    )
    
    high_priority = django_filters.BooleanFilter(
        method='filter_high_priority',
        help_text='Filter only high and critical priority actions.'
    )
    
    assigned_to_me = django_filters.BooleanFilter(
        method='filter_assigned_to_me',
        help_text='Filter actions assigned to the current user.'
    )
    
    has_evidence = django_filters.BooleanFilter(
        method='filter_has_evidence',
        help_text='Filter actions that have evidence uploaded.'
    )
    
    # Text search across multiple fields
    search = django_filters.CharFilter(
        method='filter_search',
        help_text='Search across action ID, title, and description.'
    )
    
    class Meta:
        model = RiskAction
        fields = []  # We define custom fields above
    
    def filter_overdue(self, queryset, name, value):
        """Filter actions that are overdue."""
        if value:
            today = timezone.now().date()
            return queryset.filter(
                due_date__lt=today,
                status__in=['pending', 'in_progress', 'deferred']
            )
        elif value is False:
            today = timezone.now().date()
            return queryset.filter(
                Q(due_date__gte=today) | Q(status__in=['completed', 'cancelled'])
            )
        return queryset
    
    def filter_due_soon(self, queryset, name, value):
        """Filter actions due within the next 7 days."""
        if value:
            today = timezone.now().date()
            week_from_now = today + timezone.timedelta(days=7)
            return queryset.filter(
                due_date__gte=today,
                due_date__lte=week_from_now,
                status__in=['pending', 'in_progress', 'deferred']
            )
        elif value is False:
            today = timezone.now().date()
            week_from_now = today + timezone.timedelta(days=7)
            return queryset.filter(
                Q(due_date__gt=week_from_now) | 
                Q(due_date__lt=today) | 
                Q(status__in=['completed', 'cancelled'])
            )
        return queryset
    
    def filter_active_only(self, queryset, name, value):
        """Filter only active actions."""
        if value:
            return queryset.filter(status__in=['pending', 'in_progress', 'deferred'])
        elif value is False:
            return queryset.filter(status__in=['completed', 'cancelled'])
        return queryset
    
    def filter_high_priority(self, queryset, name, value):
        """Filter high and critical priority actions."""
        if value:
            return queryset.filter(priority__in=['high', 'critical'])
        elif value is False:
            return queryset.filter(priority__in=['low', 'medium'])
        return queryset
    
    def filter_assigned_to_me(self, queryset, name, value):
        """Filter actions assigned to the current user."""
        if value and hasattr(self.request, 'user') and self.request.user.is_authenticated:
            return queryset.filter(assigned_to=self.request.user)
        return queryset
    
    def filter_has_evidence(self, queryset, name, value):
        """Filter actions with or without evidence."""
        if value:
            return queryset.filter(evidence__isnull=False).distinct()
        elif value is False:
            return queryset.filter(evidence__isnull=True)
        return queryset
    
    def filter_search(self, queryset, name, value):
        """Search across multiple text fields."""
        if value:
            return queryset.filter(
                Q(action_id__icontains=value) |
                Q(title__icontains=value) |
                Q(description__icontains=value) |
                Q(success_criteria__icontains=value) |
                Q(dependencies__icontains=value) |
                Q(risk__risk_id__icontains=value) |
                Q(risk__title__icontains=value)
            )
        return queryset