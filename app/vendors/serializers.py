"""
Vendor Management Serializers

Comprehensive serializers for vendor management API endpoints
supporting CRUD operations, filtering, and data validation.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Vendor, VendorCategory, VendorContact, VendorService, VendorNote, VendorTask

User = get_user_model()


class VendorCategorySerializer(serializers.ModelSerializer):
    """Serializer for vendor categories."""
    
    vendor_count = serializers.SerializerMethodField()
    
    class Meta:
        model = VendorCategory
        fields = [
            'id', 'name', 'description', 'color_code', 'risk_weight',
            'compliance_requirements', 'vendor_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'vendor_count']
    
    def get_vendor_count(self, obj):
        """Get the number of vendors in this category."""
        return obj.vendor_set.count()


class VendorContactSerializer(serializers.ModelSerializer):
    """Serializer for vendor contacts."""
    
    full_name = serializers.ReadOnlyField()
    contact_type_display = serializers.CharField(source='get_contact_type_display', read_only=True)
    
    class Meta:
        model = VendorContact
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'title', 'email',
            'phone', 'mobile', 'contact_type', 'contact_type_display', 'is_primary',
            'preferred_communication', 'is_active', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'full_name', 'contact_type_display']
    
    def validate(self, data):
        """Validate contact data."""
        # Ensure at least one contact method is provided
        if not any([data.get('email'), data.get('phone'), data.get('mobile')]):
            raise serializers.ValidationError(
                "At least one contact method (email, phone, or mobile) must be provided."
            )
        return data


class VendorServiceSerializer(serializers.ModelSerializer):
    """Serializer for vendor services."""
    
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    data_classification_display = serializers.CharField(source='get_data_classification_display', read_only=True)
    billing_frequency_display = serializers.CharField(source='get_billing_frequency_display', read_only=True)
    
    class Meta:
        model = VendorService
        fields = [
            'id', 'name', 'description', 'service_code', 'category', 'category_display',
            'data_classification', 'data_classification_display', 'risk_assessment_required',
            'risk_assessment_completed', 'risk_assessment_date', 'cost_per_unit',
            'billing_frequency', 'billing_frequency_display', 'is_active',
            'start_date', 'end_date', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'category_display',
            'data_classification_display', 'billing_frequency_display'
        ]


class VendorNoteSerializer(serializers.ModelSerializer):
    """Serializer for vendor notes."""
    
    created_by_name = serializers.SerializerMethodField()
    note_type_display = serializers.CharField(source='get_note_type_display', read_only=True)
    
    class Meta:
        model = VendorNote
        fields = [
            'id', 'note_type', 'note_type_display', 'title', 'content',
            'is_internal', 'created_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = ['id', 'created_at', 'created_by', 'created_by_name', 'note_type_display']
    
    def get_created_by_name(self, obj):
        """Get the full name of the user who created the note."""
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None


class VendorListSerializer(serializers.ModelSerializer):
    """Simplified serializer for vendor list views."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    vendor_type_display = serializers.CharField(source='get_vendor_type_display', read_only=True)
    risk_level_display = serializers.CharField(source='get_risk_level_display', read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    
    # Computed fields for list view
    contact_count = serializers.SerializerMethodField()
    service_count = serializers.SerializerMethodField()
    is_contract_expiring_soon = serializers.ReadOnlyField()
    days_until_contract_expiry = serializers.ReadOnlyField()
    
    class Meta:
        model = Vendor
        fields = [
            'id', 'vendor_id', 'name', 'category', 'category_name', 'status',
            'status_display', 'vendor_type', 'vendor_type_display', 'risk_level',
            'risk_level_display', 'risk_score', 'assigned_to', 'assigned_to_name',
            'contact_count', 'service_count', 'contract_end_date',
            'is_contract_expiring_soon', 'days_until_contract_expiry',
            'performance_score', 'annual_spend', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'vendor_id', 'category_name', 'status_display', 'vendor_type_display',
            'risk_level_display', 'assigned_to_name', 'contact_count', 'service_count',
            'is_contract_expiring_soon', 'days_until_contract_expiry', 'created_at', 'updated_at'
        ]
    
    def get_assigned_to_name(self, obj):
        """Get the assigned user's name."""
        if obj.assigned_to:
            return obj.assigned_to.get_full_name() or obj.assigned_to.username
        return None
    
    def get_contact_count(self, obj):
        """Get the number of contacts for this vendor."""
        return obj.contacts.filter(is_active=True).count()
    
    def get_service_count(self, obj):
        """Get the number of services for this vendor."""
        return obj.services.filter(is_active=True).count()


class VendorDetailSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for vendor detail views."""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    vendor_type_display = serializers.CharField(source='get_vendor_type_display', read_only=True)
    risk_level_display = serializers.CharField(source='get_risk_level_display', read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    
    # Related data
    contacts = VendorContactSerializer(many=True, read_only=True)
    services = VendorServiceSerializer(many=True, read_only=True)
    
    # Computed fields
    full_address = serializers.ReadOnlyField()
    is_contract_expiring_soon = serializers.ReadOnlyField()
    days_until_contract_expiry = serializers.ReadOnlyField()
    
    # Statistics
    contact_count = serializers.SerializerMethodField()
    service_count = serializers.SerializerMethodField()
    active_service_count = serializers.SerializerMethodField()
    note_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Vendor
        fields = [
            # Basic Information
            'id', 'vendor_id', 'name', 'legal_name', 'category', 'category_name',
            'business_description', 'website', 'tax_id', 'duns_number',
            
            # Address
            'address_line1', 'address_line2', 'city', 'state_province', 'postal_code',
            'country', 'full_address',
            
            # Status and Classification  
            'status', 'status_display', 'vendor_type', 'vendor_type_display',
            
            # Risk Assessment
            'risk_level', 'risk_level_display', 'risk_score',
            
            # Financial
            'annual_spend', 'credit_rating', 'payment_terms',
            
            # Compliance
            'certifications', 'compliance_status', 'data_processing_agreement',
            'security_assessment_completed', 'security_assessment_date',
            
            # Relationship Management
            'assigned_to', 'assigned_to_name', 'relationship_start_date',
            
            # Contract Information
            'primary_contract_number', 'contract_start_date', 'contract_end_date',
            'auto_renewal', 'renewal_notice_days', 'is_contract_expiring_soon',
            'days_until_contract_expiry',
            
            # Performance
            'performance_score', 'last_performance_review',
            
            # Additional Information
            'notes', 'tags',
            
            # Related Data
            'contacts', 'services',
            
            # Statistics
            'contact_count', 'service_count', 'active_service_count', 'note_count',
            
            # Metadata
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = [
            'id', 'vendor_id', 'full_address', 'is_contract_expiring_soon',
            'days_until_contract_expiry', 'contacts', 'services',
            'contact_count', 'service_count', 'active_service_count', 'note_count',
            'created_at', 'updated_at', 'created_by', 'created_by_name',
            'category_name', 'status_display', 'vendor_type_display',
            'risk_level_display', 'assigned_to_name'
        ]
    
    def get_assigned_to_name(self, obj):
        """Get the assigned user's name."""
        if obj.assigned_to:
            return obj.assigned_to.get_full_name() or obj.assigned_to.username
        return None
    
    def get_created_by_name(self, obj):
        """Get the creator's name."""
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None
    
    def get_contact_count(self, obj):
        """Get total contact count."""
        return obj.contacts.count()
    
    def get_service_count(self, obj):
        """Get total service count."""
        return obj.services.count()
    
    def get_active_service_count(self, obj):
        """Get active service count."""
        return obj.services.filter(is_active=True).count()
    
    def get_note_count(self, obj):
        """Get note count."""
        return obj.vendor_notes.count()


class VendorCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating vendors."""
    
    class Meta:
        model = Vendor
        fields = [
            # Basic Information
            'name', 'legal_name', 'category', 'business_description', 'website',
            'tax_id', 'duns_number',
            
            # Address
            'address_line1', 'address_line2', 'city', 'state_province', 'postal_code', 'country',
            
            # Status and Classification
            'status', 'vendor_type',
            
            # Risk Assessment
            'risk_level', 'risk_score',
            
            # Financial
            'annual_spend', 'credit_rating', 'payment_terms',
            
            # Compliance
            'certifications', 'compliance_status', 'data_processing_agreement',
            'security_assessment_completed', 'security_assessment_date',
            
            # Relationship Management
            'assigned_to', 'relationship_start_date',
            
            # Contract Information
            'primary_contract_number', 'contract_start_date', 'contract_end_date',
            'auto_renewal', 'renewal_notice_days',
            
            # Performance
            'performance_score', 'last_performance_review',
            
            # Additional Information
            'notes', 'tags'
        ]
    
    def validate_name(self, value):
        """Validate vendor name."""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Vendor name must be at least 2 characters long.")
        return value.strip()
    
    def validate_risk_score(self, value):
        """Validate risk score range."""
        if value is not None and (value < 0 or value > 100):
            raise serializers.ValidationError("Risk score must be between 0 and 100.")
        return value
    
    def validate_performance_score(self, value):
        """Validate performance score range."""
        if value is not None and (value < 0 or value > 100):
            raise serializers.ValidationError("Performance score must be between 0 and 100.")
        return value
    
    def validate(self, data):
        """Validate vendor data."""
        # Validate contract dates
        if data.get('contract_start_date') and data.get('contract_end_date'):
            if data['contract_start_date'] >= data['contract_end_date']:
                raise serializers.ValidationError(
                    "Contract start date must be before contract end date."
                )
        
        # Validate renewal notice days
        if data.get('renewal_notice_days') is not None and data['renewal_notice_days'] < 0:
            raise serializers.ValidationError(
                "Renewal notice days must be a positive number."
            )
        
        return data


class VendorSummarySerializer(serializers.Serializer):
    """Serializer for vendor summary statistics."""
    
    total_vendors = serializers.IntegerField()
    active_vendors = serializers.IntegerField()
    inactive_vendors = serializers.IntegerField()
    under_review_vendors = serializers.IntegerField()
    
    # Risk distribution
    critical_risk_vendors = serializers.IntegerField()
    high_risk_vendors = serializers.IntegerField()
    medium_risk_vendors = serializers.IntegerField()
    low_risk_vendors = serializers.IntegerField()
    
    # Contract management
    contracts_expiring_soon = serializers.IntegerField()
    expired_contracts = serializers.IntegerField()
    auto_renewal_contracts = serializers.IntegerField()
    
    # Categories
    vendors_by_category = serializers.DictField()
    
    # Financial
    total_annual_spend = serializers.DecimalField(max_digits=15, decimal_places=2, allow_null=True)
    average_performance_score = serializers.DecimalField(max_digits=4, decimal_places=2, allow_null=True)
    
    # Compliance
    vendors_with_dpa = serializers.IntegerField()
    vendors_with_security_assessment = serializers.IntegerField()
    
    # Services
    total_services = serializers.IntegerField()
    active_services = serializers.IntegerField()


class BulkVendorCreateSerializer(serializers.Serializer):
    """Serializer for bulk vendor creation."""
    
    vendors = VendorCreateUpdateSerializer(many=True)
    
    def validate_vendors(self, value):
        """Validate the list of vendors."""
        if not value:
            raise serializers.ValidationError("At least one vendor must be provided.")
        
        if len(value) > 100:
            raise serializers.ValidationError("Cannot create more than 100 vendors at once.")
        
        # Check for duplicate names
        names = [vendor['name'] for vendor in value if 'name' in vendor]
        if len(names) != len(set(names)):
            raise serializers.ValidationError("Duplicate vendor names are not allowed.")
        
        return value
    
    def create(self, validated_data):
        """Create multiple vendors in bulk."""
        vendors_data = validated_data['vendors']
        vendors = []
        
        for vendor_data in vendors_data:
            vendor_data['created_by'] = self.context['request'].user
            vendor = Vendor.objects.create(**vendor_data)
            vendors.append(vendor)
        
        return vendors


class VendorTaskListSerializer(serializers.ModelSerializer):
    """Serializer for vendor task list view."""
    
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    vendor_id = serializers.CharField(source='vendor.vendor_id', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    days_until_due = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    
    class Meta:
        model = VendorTask
        fields = [
            'id', 'task_id', 'vendor', 'vendor_name', 'vendor_id',
            'task_type', 'task_type_display', 'title', 'due_date',
            'priority', 'priority_display', 'status', 'status_display',
            'assigned_to', 'assigned_to_name', 'days_until_due', 'is_overdue',
            'auto_generated', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'task_id', 'vendor_name', 'vendor_id', 'assigned_to_name',
            'task_type_display', 'priority_display', 'status_display',
            'days_until_due', 'is_overdue', 'auto_generated', 'created_at', 'updated_at'
        ]


class VendorTaskDetailSerializer(serializers.ModelSerializer):
    """Serializer for vendor task detail view."""
    
    vendor_details = VendorListSerializer(source='vendor', read_only=True)
    assigned_to_details = serializers.SerializerMethodField()
    created_by_details = serializers.SerializerMethodField()
    service_details = serializers.SerializerMethodField()
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # Computed fields
    days_until_due = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    should_send_reminder = serializers.ReadOnlyField()
    next_reminder_date = serializers.ReadOnlyField()
    
    class Meta:
        model = VendorTask
        fields = [
            'id', 'task_id', 'vendor', 'vendor_details', 'task_type', 'task_type_display',
            'title', 'description', 'due_date', 'start_date', 'completed_date',
            'priority', 'priority_display', 'status', 'status_display',
            'assigned_to', 'assigned_to_details', 'created_by', 'created_by_details',
            'reminder_days', 'last_reminder_sent', 'reminder_recipients',
            'related_contract_number', 'service_reference', 'service_details',
            'completion_notes', 'attachments', 'is_recurring', 'recurrence_pattern',
            'parent_task', 'auto_generated', 'generation_source',
            'days_until_due', 'is_overdue', 'should_send_reminder', 'next_reminder_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'task_id', 'vendor_details', 'task_type_display', 'priority_display',
            'status_display', 'assigned_to_details', 'created_by_details', 'service_details',
            'days_until_due', 'is_overdue', 'should_send_reminder', 'next_reminder_date',
            'auto_generated', 'generation_source', 'created_at', 'updated_at'
        ]
    
    def get_assigned_to_details(self, obj):
        """Get assigned user details."""
        if obj.assigned_to:
            return {
                'id': obj.assigned_to.id,
                'username': obj.assigned_to.username,
                'full_name': obj.assigned_to.get_full_name(),
                'email': obj.assigned_to.email,
            }
        return None
    
    def get_created_by_details(self, obj):
        """Get creator user details."""
        if obj.created_by:
            return {
                'id': obj.created_by.id,
                'username': obj.created_by.username,
                'full_name': obj.created_by.get_full_name(),
            }
        return None
    
    def get_service_details(self, obj):
        """Get related service details."""
        if obj.service_reference:
            return {
                'id': obj.service_reference.id,
                'service_name': obj.service_reference.service_name,
                'service_category': obj.service_reference.get_service_category_display(),
            }
        return None


class VendorTaskCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating vendor tasks."""
    
    class Meta:
        model = VendorTask
        fields = [
            'vendor', 'task_type', 'title', 'description', 'due_date', 'start_date',
            'priority', 'status', 'assigned_to', 'reminder_days', 'reminder_recipients',
            'related_contract_number', 'service_reference', 'completion_notes',
            'attachments', 'is_recurring', 'recurrence_pattern'
        ]
    
    def validate_due_date(self, value):
        """Validate due date is not in the past for new tasks."""
        from django.utils import timezone
        
        if not self.instance and value < timezone.now().date():
            raise serializers.ValidationError("Due date cannot be in the past for new tasks.")
        
        return value
    
    def validate_recurrence_pattern(self, value):
        """Validate recurrence pattern structure."""
        if value:
            required_fields = ['frequency']
            for field in required_fields:
                if field not in value:
                    raise serializers.ValidationError(f"Recurrence pattern must include '{field}' field.")
            
            valid_frequencies = ['monthly', 'quarterly', 'yearly']
            if value['frequency'] not in valid_frequencies:
                raise serializers.ValidationError(f"Frequency must be one of: {', '.join(valid_frequencies)}")
        
        return value
    
    def validate_reminder_days(self, value):
        """Validate reminder days configuration."""
        if value:
            if not isinstance(value, list):
                raise serializers.ValidationError("Reminder days must be a list of integers.")
            
            if not all(isinstance(day, int) and day > 0 for day in value):
                raise serializers.ValidationError("Reminder days must be positive integers.")
            
            if len(value) > 10:
                raise serializers.ValidationError("Cannot have more than 10 reminder intervals.")
        
        return value
    
    def create(self, validated_data):
        """Create a new vendor task."""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class VendorTaskStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating task status."""
    
    status = serializers.ChoiceField(choices=VendorTask.STATUS_CHOICES)
    completion_notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        """Validate status update."""
        if data['status'] == 'completed' and not data.get('completion_notes'):
            raise serializers.ValidationError({
                'completion_notes': 'Completion notes are required when marking task as completed.'
            })
        
        return data


class VendorTaskBulkActionSerializer(serializers.Serializer):
    """Serializer for bulk task actions."""
    
    task_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=100
    )
    action = serializers.ChoiceField(choices=[
        ('update_status', 'Update Status'),
        ('assign_user', 'Assign User'),
        ('update_priority', 'Update Priority'),
        ('send_reminders', 'Send Reminders'),
    ])
    
    # Action-specific fields
    status = serializers.ChoiceField(choices=VendorTask.STATUS_CHOICES, required=False)
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False
    )
    priority = serializers.ChoiceField(choices=VendorTask.PRIORITY_CHOICES, required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        """Validate bulk action parameters."""
        action = data['action']
        
        if action == 'update_status' and not data.get('status'):
            raise serializers.ValidationError({'status': 'Status is required for status update action.'})
        
        if action == 'assign_user' and not data.get('assigned_to'):
            raise serializers.ValidationError({'assigned_to': 'User is required for assign user action.'})
        
        if action == 'update_priority' and not data.get('priority'):
            raise serializers.ValidationError({'priority': 'Priority is required for priority update action.'})
        
        return data


class VendorTaskSummarySerializer(serializers.Serializer):
    """Serializer for vendor task summary statistics."""
    
    # Total counts
    total_tasks = serializers.IntegerField()
    active_tasks = serializers.IntegerField()
    completed_tasks = serializers.IntegerField()
    overdue_tasks = serializers.IntegerField()
    
    # Status breakdown
    status_breakdown = serializers.DictField()
    
    # Priority breakdown
    priority_breakdown = serializers.DictField()
    
    # Task type breakdown
    task_type_breakdown = serializers.DictField()
    
    # Due date analysis
    due_this_week = serializers.IntegerField()
    due_this_month = serializers.IntegerField()
    due_next_month = serializers.IntegerField()
    
    # Assignment analysis
    assigned_tasks = serializers.IntegerField()
    unassigned_tasks = serializers.IntegerField()
    
    # Automation statistics
    auto_generated_tasks = serializers.IntegerField()
    manual_tasks = serializers.IntegerField()
    
    # Performance metrics
    average_completion_time = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    on_time_completion_rate = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)


class VendorTaskReminderSerializer(serializers.Serializer):
    """Serializer for task reminder operations."""
    
    task_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="Specific task IDs to send reminders for (optional)"
    )
    force_send = serializers.BooleanField(
        default=False,
        help_text="Send reminders even if not scheduled for today"
    )
    additional_recipients = serializers.ListField(
        child=serializers.EmailField(),
        required=False,
        help_text="Additional email addresses to include"
    )
    
    def validate_task_ids(self, value):
        """Validate task IDs exist and are accessible."""
        if value:
            existing_tasks = VendorTask.objects.filter(id__in=value).count()
            if existing_tasks != len(value):
                raise serializers.ValidationError("One or more task IDs are invalid.")
        
        return value