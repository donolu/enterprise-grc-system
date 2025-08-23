"""
Vendor Management Filters

Advanced filtering capabilities for vendor management API endpoints
supporting complex queries, date ranges, and multi-field filtering.
"""

import django_filters
from django.db.models import Q
from django.utils import timezone
from .models import Vendor, VendorContact, VendorService, VendorNote, VendorCategory


class VendorFilter(django_filters.FilterSet):
    """Advanced filtering for vendors with support for complex queries."""
    
    # Basic filters
    name = django_filters.CharFilter(lookup_expr='icontains')
    vendor_id = django_filters.CharFilter(lookup_expr='icontains')
    status = django_filters.MultipleChoiceFilter(choices=Vendor.STATUS_CHOICES)
    vendor_type = django_filters.MultipleChoiceFilter(choices=Vendor.VENDOR_TYPE_CHOICES)
    risk_level = django_filters.MultipleChoiceFilter(choices=Vendor.RISK_LEVEL_CHOICES)
    
    # Category and assignment filters
    category = django_filters.ModelMultipleChoiceFilter(queryset=VendorCategory.objects.all())
    category_name = django_filters.CharFilter(field_name='category__name', lookup_expr='icontains')
    assigned_to = django_filters.NumberFilter()
    assigned_to_me = django_filters.BooleanFilter(method='filter_assigned_to_me')
    
    # Financial filters
    annual_spend_min = django_filters.NumberFilter(field_name='annual_spend', lookup_expr='gte')
    annual_spend_max = django_filters.NumberFilter(field_name='annual_spend', lookup_expr='lte')
    performance_score_min = django_filters.NumberFilter(field_name='performance_score', lookup_expr='gte')
    performance_score_max = django_filters.NumberFilter(field_name='performance_score', lookup_expr='lte')
    risk_score_min = django_filters.NumberFilter(field_name='risk_score', lookup_expr='gte')
    risk_score_max = django_filters.NumberFilter(field_name='risk_score', lookup_expr='lte')
    
    # Date filters
    created_after = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    relationship_started_after = django_filters.DateFilter(field_name='relationship_start_date', lookup_expr='gte')
    relationship_started_before = django_filters.DateFilter(field_name='relationship_start_date', lookup_expr='lte')
    
    # Contract filters
    contract_expires_after = django_filters.DateFilter(field_name='contract_end_date', lookup_expr='gte')
    contract_expires_before = django_filters.DateFilter(field_name='contract_end_date', lookup_expr='lte')
    contract_expiring_soon = django_filters.BooleanFilter(method='filter_contract_expiring_soon')
    contract_expired = django_filters.BooleanFilter(method='filter_contract_expired')
    auto_renewal = django_filters.BooleanFilter()
    
    # Compliance filters
    has_dpa = django_filters.BooleanFilter(field_name='data_processing_agreement')
    security_assessment_completed = django_filters.BooleanFilter()
    security_assessment_after = django_filters.DateFilter(field_name='security_assessment_date', lookup_expr='gte')
    security_assessment_before = django_filters.DateFilter(field_name='security_assessment_date', lookup_expr='lte')
    
    # Regional filters
    operating_region = django_filters.CharFilter(method='filter_operating_region')
    primary_region = django_filters.CharFilter(lookup_expr='iexact')
    
    # Location filters
    country = django_filters.CharFilter(lookup_expr='icontains')
    city = django_filters.CharFilter(lookup_expr='icontains')
    
    # Boolean flags
    has_website = django_filters.BooleanFilter(method='filter_has_website')
    has_contacts = django_filters.BooleanFilter(method='filter_has_contacts')
    has_services = django_filters.BooleanFilter(method='filter_has_services')
    has_performance_score = django_filters.BooleanFilter(method='filter_has_performance_score')
    
    # Tag filter
    tags = django_filters.CharFilter(method='filter_tags')
    
    class Meta:
        model = Vendor
        fields = []
    
    def filter_assigned_to_me(self, queryset, name, value):
        """Filter vendors assigned to the current user."""
        if value and hasattr(self.request, 'user'):
            return queryset.filter(assigned_to=self.request.user)
        return queryset
    
    def filter_contract_expiring_soon(self, queryset, name, value):
        """Filter vendors with contracts expiring within renewal notice period."""
        if value:
            today = timezone.now().date()
            return queryset.filter(
                contract_end_date__isnull=False,
                contract_end_date__gte=today
            ).extra(
                where=["contract_end_date <= %s + INTERVAL renewal_notice_days DAY"],
                params=[today]
            )
        return queryset
    
    def filter_contract_expired(self, queryset, name, value):
        """Filter vendors with expired contracts."""
        if value:
            today = timezone.now().date()
            return queryset.filter(contract_end_date__lt=today)
        return queryset
    
    def filter_operating_region(self, queryset, name, value):
        """Filter vendors operating in a specific region."""
        if value:
            return queryset.filter(operating_regions__contains=[value])
        return queryset
    
    def filter_has_website(self, queryset, name, value):
        """Filter vendors that have/don't have a website."""
        if value:
            return queryset.exclude(website='')
        else:
            return queryset.filter(Q(website='') | Q(website__isnull=True))
    
    def filter_has_contacts(self, queryset, name, value):
        """Filter vendors that have/don't have contacts."""
        if value:
            return queryset.filter(contacts__isnull=False).distinct()
        else:
            return queryset.filter(contacts__isnull=True)
    
    def filter_has_services(self, queryset, name, value):
        """Filter vendors that have/don't have services."""
        if value:
            return queryset.filter(services__isnull=False).distinct()
        else:
            return queryset.filter(services__isnull=True)
    
    def filter_has_performance_score(self, queryset, name, value):
        """Filter vendors that have/don't have a performance score."""
        if value:
            return queryset.exclude(performance_score__isnull=True)
        else:
            return queryset.filter(performance_score__isnull=True)
    
    def filter_tags(self, queryset, name, value):
        """Filter vendors by tags (comma-separated)."""
        if value:
            tags = [tag.strip() for tag in value.split(',')]
            return queryset.filter(tags__overlap=tags)
        return queryset


class VendorContactFilter(django_filters.FilterSet):
    """Filtering for vendor contacts."""
    
    # Basic filters
    vendor = django_filters.NumberFilter()
    vendor_name = django_filters.CharFilter(field_name='vendor__name', lookup_expr='icontains')
    first_name = django_filters.CharFilter(lookup_expr='icontains')
    last_name = django_filters.CharFilter(lookup_expr='icontains')
    full_name = django_filters.CharFilter(method='filter_full_name')
    email = django_filters.CharFilter(lookup_expr='icontains')
    
    # Contact type and status
    contact_type = django_filters.MultipleChoiceFilter(choices=VendorContact.CONTACT_TYPE_CHOICES)
    is_primary = django_filters.BooleanFilter()
    is_active = django_filters.BooleanFilter()
    
    # Communication preferences
    preferred_communication = django_filters.ChoiceFilter(
        choices=[('email', 'Email'), ('phone', 'Phone'), ('mobile', 'Mobile')]
    )
    
    # Contact methods
    has_phone = django_filters.BooleanFilter(method='filter_has_phone')
    has_mobile = django_filters.BooleanFilter(method='filter_has_mobile')
    
    class Meta:
        model = VendorContact
        fields = []
    
    def filter_full_name(self, queryset, name, value):
        """Filter by full name (first + last name)."""
        if value:
            names = value.split()
            if len(names) == 1:
                return queryset.filter(
                    Q(first_name__icontains=names[0]) | Q(last_name__icontains=names[0])
                )
            elif len(names) >= 2:
                return queryset.filter(
                    first_name__icontains=names[0],
                    last_name__icontains=' '.join(names[1:])
                )
        return queryset
    
    def filter_has_phone(self, queryset, name, value):
        """Filter contacts that have/don't have phone number."""
        if value:
            return queryset.exclude(phone='')
        else:
            return queryset.filter(Q(phone='') | Q(phone__isnull=True))
    
    def filter_has_mobile(self, queryset, name, value):
        """Filter contacts that have/don't have mobile number."""
        if value:
            return queryset.exclude(mobile='')
        else:
            return queryset.filter(Q(mobile='') | Q(mobile__isnull=True))


class VendorServiceFilter(django_filters.FilterSet):
    """Filtering for vendor services."""
    
    # Basic filters
    vendor = django_filters.NumberFilter()
    vendor_name = django_filters.CharFilter(field_name='vendor__name', lookup_expr='icontains')
    name = django_filters.CharFilter(lookup_expr='icontains')
    service_code = django_filters.CharFilter(lookup_expr='icontains')
    category = django_filters.MultipleChoiceFilter(choices=VendorService.SERVICE_CATEGORY_CHOICES)
    
    # Data and risk filters
    data_classification = django_filters.MultipleChoiceFilter(choices=VendorService.DATA_CLASSIFICATION_CHOICES)
    risk_assessment_required = django_filters.BooleanFilter()
    risk_assessment_completed = django_filters.BooleanFilter()
    risk_assessment_after = django_filters.DateFilter(field_name='risk_assessment_date', lookup_expr='gte')
    risk_assessment_before = django_filters.DateFilter(field_name='risk_assessment_date', lookup_expr='lte')
    
    # Financial filters
    cost_per_unit_min = django_filters.NumberFilter(field_name='cost_per_unit', lookup_expr='gte')
    cost_per_unit_max = django_filters.NumberFilter(field_name='cost_per_unit', lookup_expr='lte')
    billing_frequency = django_filters.MultipleChoiceFilter(
        choices=[('one_time', 'One Time'), ('monthly', 'Monthly'), ('quarterly', 'Quarterly'), ('annually', 'Annually')]
    )
    
    # Status and date filters
    is_active = django_filters.BooleanFilter()
    start_date_after = django_filters.DateFilter(field_name='start_date', lookup_expr='gte')
    start_date_before = django_filters.DateFilter(field_name='start_date', lookup_expr='lte')
    end_date_after = django_filters.DateFilter(field_name='end_date', lookup_expr='gte')
    end_date_before = django_filters.DateFilter(field_name='end_date', lookup_expr='lte')
    
    # Boolean flags
    has_cost = django_filters.BooleanFilter(method='filter_has_cost')
    expiring_soon = django_filters.BooleanFilter(method='filter_expiring_soon')
    
    class Meta:
        model = VendorService
        fields = []
    
    def filter_has_cost(self, queryset, name, value):
        """Filter services that have/don't have cost information."""
        if value:
            return queryset.exclude(cost_per_unit__isnull=True)
        else:
            return queryset.filter(cost_per_unit__isnull=True)
    
    def filter_expiring_soon(self, queryset, name, value):
        """Filter services expiring within 30 days."""
        if value:
            today = timezone.now().date()
            future_date = today + timezone.timedelta(days=30)
            return queryset.filter(
                end_date__isnull=False,
                end_date__gte=today,
                end_date__lte=future_date
            )
        return queryset


class VendorNoteFilter(django_filters.FilterSet):
    """Filtering for vendor notes."""
    
    # Basic filters
    vendor = django_filters.NumberFilter()
    vendor_name = django_filters.CharFilter(field_name='vendor__name', lookup_expr='icontains')
    note_type = django_filters.MultipleChoiceFilter(choices=VendorNote.NOTE_TYPE_CHOICES)
    title = django_filters.CharFilter(lookup_expr='icontains')
    content = django_filters.CharFilter(lookup_expr='icontains')
    
    # Creator and visibility
    created_by = django_filters.NumberFilter()
    created_by_me = django_filters.BooleanFilter(method='filter_created_by_me')
    is_internal = django_filters.BooleanFilter()
    
    # Date filters
    created_after = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = VendorNote
        fields = []
    
    def filter_created_by_me(self, queryset, name, value):
        """Filter notes created by the current user."""
        if value and hasattr(self.request, 'user'):
            return queryset.filter(created_by=self.request.user)
        return queryset