from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import (
    Risk, RiskCategory, RiskMatrix, RiskNote,
    RiskAction, RiskActionNote, RiskActionEvidence, 
    RiskActionReminderConfiguration
)

User = get_user_model()


class RiskCategorySerializer(serializers.ModelSerializer):
    """Serializer for Risk Categories."""
    
    risk_count = serializers.SerializerMethodField()
    
    class Meta:
        model = RiskCategory
        fields = [
            'id', 'name', 'description', 'color',
            'risk_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_risk_count(self, obj):
        """Get count of risks in this category."""
        return obj.risks.count()


class RiskMatrixSerializer(serializers.ModelSerializer):
    """Serializer for Risk Matrix configurations."""
    
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = RiskMatrix
        fields = [
            'id', 'name', 'description', 'is_default',
            'impact_levels', 'likelihood_levels', 'matrix_config',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']
    
    def validate_matrix_config(self, value):
        """Validate matrix configuration structure."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Matrix configuration must be a dictionary")
        
        impact_levels = self.initial_data.get('impact_levels', 5)
        likelihood_levels = self.initial_data.get('likelihood_levels', 5)
        
        # Validate structure
        for impact in range(1, impact_levels + 1):
            impact_str = str(impact)
            if impact_str not in value:
                raise serializers.ValidationError(f"Missing impact level {impact} in matrix configuration")
            
            for likelihood in range(1, likelihood_levels + 1):
                likelihood_str = str(likelihood)
                if likelihood_str not in value[impact_str]:
                    raise serializers.ValidationError(f"Missing likelihood level {likelihood} for impact {impact}")
                
                level = value[impact_str][likelihood_str]
                if level not in ['low', 'medium', 'high', 'critical']:
                    raise serializers.ValidationError(f"Invalid risk level '{level}' at impact {impact}, likelihood {likelihood}")
        
        return value


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user serializer for risk ownership."""
    
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name']
        read_only_fields = ['username', 'email', 'first_name', 'last_name', 'full_name']


class RiskNoteSerializer(serializers.ModelSerializer):
    """Serializer for Risk Notes."""
    
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = RiskNote
        fields = [
            'id', 'note', 'note_type', 'created_at',
            'created_by', 'created_by_name'
        ]
        read_only_fields = ['created_at', 'created_by']


class RiskListSerializer(serializers.ModelSerializer):
    """Serializer for Risk list view with essential fields."""
    
    risk_level_display = serializers.CharField(source='get_risk_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    risk_owner_name = serializers.CharField(source='risk_owner.get_full_name', read_only=True)
    risk_score = serializers.IntegerField(read_only=True)
    is_overdue_for_review = serializers.BooleanField(read_only=True)
    days_until_review = serializers.IntegerField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    risk_level_color = serializers.CharField(read_only=True)
    status_display_color = serializers.CharField(read_only=True)
    
    class Meta:
        model = Risk
        fields = [
            'id', 'risk_id', 'title', 'description',
            'impact', 'likelihood', 'risk_level', 'risk_level_display', 'risk_level_color',
            'status', 'status_display', 'status_display_color',
            'category', 'category_name',
            'risk_owner', 'risk_owner_name',
            'risk_score', 'identified_date', 'last_assessed_date', 'next_review_date',
            'is_overdue_for_review', 'days_until_review', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'risk_id', 'risk_level', 'risk_score', 'is_overdue_for_review',
            'days_until_review', 'is_active', 'created_at', 'updated_at'
        ]


class RiskDetailSerializer(serializers.ModelSerializer):
    """Detailed Risk serializer with all fields and related data."""
    
    risk_level_display = serializers.CharField(source='get_risk_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    treatment_strategy_display = serializers.CharField(source='get_treatment_strategy_display', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    risk_owner_name = serializers.CharField(source='risk_owner.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    risk_matrix_name = serializers.CharField(source='risk_matrix.name', read_only=True)
    
    # Computed fields
    risk_score = serializers.IntegerField(read_only=True)
    is_overdue_for_review = serializers.BooleanField(read_only=True)
    days_until_review = serializers.IntegerField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    risk_level_color = serializers.CharField(read_only=True)
    status_display_color = serializers.CharField(read_only=True)
    
    # Related data
    category = RiskCategorySerializer(read_only=True)
    risk_owner = UserBasicSerializer(read_only=True)
    risk_matrix = RiskMatrixSerializer(read_only=True)
    notes = RiskNoteSerializer(many=True, read_only=True)
    
    class Meta:
        model = Risk
        fields = [
            'id', 'risk_id', 'title', 'description',
            'impact', 'likelihood', 'risk_level', 'risk_level_display', 'risk_level_color',
            'status', 'status_display', 'status_display_color',
            'treatment_strategy', 'treatment_strategy_display', 'treatment_description',
            'category', 'category_name',
            'risk_owner', 'risk_owner_name',
            'risk_matrix', 'risk_matrix_name',
            'identified_date', 'last_assessed_date', 'next_review_date', 'closed_date',
            'potential_impact_description', 'current_controls',
            'risk_score', 'is_overdue_for_review', 'days_until_review', 'is_active',
            'created_at', 'updated_at', 'created_by', 'created_by_name',
            'notes'
        ]
        read_only_fields = [
            'risk_id', 'risk_level', 'risk_score', 'is_overdue_for_review',
            'days_until_review', 'is_active', 'closed_date',
            'created_at', 'updated_at', 'created_by'
        ]


class RiskCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating risks."""
    
    class Meta:
        model = Risk
        fields = [
            'title', 'description', 'category', 'impact', 'likelihood',
            'status', 'treatment_strategy', 'treatment_description',
            'risk_owner', 'risk_matrix',
            'identified_date', 'next_review_date',
            'potential_impact_description', 'current_controls'
        ]
    
    def validate_impact(self, value):
        """Validate impact level is within acceptable range."""
        if value < 1 or value > 5:
            raise serializers.ValidationError("Impact must be between 1 and 5")
        return value
    
    def validate_likelihood(self, value):
        """Validate likelihood level is within acceptable range."""
        if value < 1 or value > 5:
            raise serializers.ValidationError("Likelihood must be between 1 and 5")
        return value
    
    def validate(self, data):
        """Cross-field validation."""
        # Ensure treatment strategy is provided when status requires it
        status = data.get('status')
        treatment_strategy = data.get('treatment_strategy')
        
        if status in ['treatment_planned', 'treatment_in_progress', 'mitigated'] and not treatment_strategy:
            raise serializers.ValidationError({
                'treatment_strategy': 'Treatment strategy is required for this status'
            })
        
        return data


class RiskStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating risk status with optional notes."""
    
    status = serializers.ChoiceField(choices=Risk.STATUS_CHOICES)
    treatment_strategy = serializers.ChoiceField(choices=Risk.TREATMENT_STRATEGIES, required=False)
    treatment_description = serializers.CharField(required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True)
    next_review_date = serializers.DateField(required=False, allow_null=True)
    
    def validate(self, data):
        """Cross-field validation for status updates."""
        status = data.get('status')
        treatment_strategy = data.get('treatment_strategy')
        
        # Require treatment strategy for certain statuses
        if status in ['treatment_planned', 'treatment_in_progress', 'mitigated'] and not treatment_strategy:
            raise serializers.ValidationError({
                'treatment_strategy': 'Treatment strategy is required for this status'
            })
        
        return data
    
    def update_risk_status(self, risk):
        """Update risk status and create note if provided."""
        from django.db import transaction
        
        with transaction.atomic():
            # Update risk fields
            risk.status = self.validated_data['status']
            
            if 'treatment_strategy' in self.validated_data:
                risk.treatment_strategy = self.validated_data['treatment_strategy']
            
            if 'treatment_description' in self.validated_data:
                risk.treatment_description = self.validated_data['treatment_description']
            
            if 'next_review_date' in self.validated_data:
                risk.next_review_date = self.validated_data['next_review_date']
            
            risk.save()
            
            # Create note if provided
            note_text = self.validated_data.get('note')
            if note_text:
                RiskNote.objects.create(
                    risk=risk,
                    note=note_text,
                    note_type='status_change',
                    created_by=self.context['request'].user
                )
        
        return risk


class BulkRiskCreateSerializer(serializers.Serializer):
    """Serializer for bulk risk creation."""
    
    category = serializers.PrimaryKeyRelatedField(
        queryset=RiskCategory.objects.all(),
        required=False,
        allow_null=True
    )
    risk_owner = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True
    )
    risk_matrix = serializers.PrimaryKeyRelatedField(
        queryset=RiskMatrix.objects.all(),
        required=False,
        allow_null=True
    )
    default_impact = serializers.IntegerField(min_value=1, max_value=5, default=3)
    default_likelihood = serializers.IntegerField(min_value=1, max_value=5, default=3)
    next_review_date = serializers.DateField(required=False, allow_null=True)
    
    risks = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        max_length=100,
        help_text='List of risk dictionaries with title, description, and optional overrides'
    )
    
    def validate_risks(self, value):
        """Validate individual risk data."""
        required_fields = ['title', 'description']
        
        for i, risk_data in enumerate(value):
            # Check required fields
            for field in required_fields:
                if field not in risk_data or not risk_data[field].strip():
                    raise serializers.ValidationError(
                        f"Risk {i+1}: '{field}' is required and cannot be empty"
                    )
            
            # Validate optional impact/likelihood overrides
            if 'impact' in risk_data:
                impact = risk_data['impact']
                if not isinstance(impact, int) or impact < 1 or impact > 5:
                    raise serializers.ValidationError(
                        f"Risk {i+1}: 'impact' must be an integer between 1 and 5"
                    )
            
            if 'likelihood' in risk_data:
                likelihood = risk_data['likelihood']
                if not isinstance(likelihood, int) or likelihood < 1 or likelihood > 5:
                    raise serializers.ValidationError(
                        f"Risk {i+1}: 'likelihood' must be an integer between 1 and 5"
                    )
        
        return value
    
    def create_bulk_risks(self):
        """Create multiple risks in bulk."""
        from django.db import transaction
        
        created_risks = []
        errors = []
        
        with transaction.atomic():
            for i, risk_data in enumerate(self.validated_data['risks']):
                try:
                    risk = Risk.objects.create(
                        title=risk_data['title'],
                        description=risk_data['description'],
                        category=self.validated_data.get('category'),
                        risk_owner=self.validated_data.get('risk_owner'),
                        risk_matrix=self.validated_data.get('risk_matrix'),
                        impact=risk_data.get('impact', self.validated_data['default_impact']),
                        likelihood=risk_data.get('likelihood', self.validated_data['default_likelihood']),
                        next_review_date=self.validated_data.get('next_review_date'),
                        potential_impact_description=risk_data.get('potential_impact_description', ''),
                        current_controls=risk_data.get('current_controls', ''),
                        created_by=self.context['request'].user
                    )
                    created_risks.append(risk)
                    
                except Exception as e:
                    errors.append({
                        'index': i,
                        'title': risk_data.get('title', ''),
                        'error': str(e)
                    })
        
        return created_risks, errors


class RiskSummarySerializer(serializers.Serializer):
    """Serializer for risk summary statistics."""
    
    total_risks = serializers.IntegerField()
    active_risks = serializers.IntegerField()
    overdue_reviews = serializers.IntegerField()
    
    by_risk_level = serializers.DictField()
    by_status = serializers.DictField()
    by_category = serializers.DictField()
    by_treatment_strategy = serializers.DictField()
    
    recent_risks = RiskListSerializer(many=True, read_only=True)
    high_priority_risks = RiskListSerializer(many=True, read_only=True)
    overdue_review_risks = RiskListSerializer(many=True, read_only=True)


# Risk Action Serializers
class RiskActionNoteSerializer(serializers.ModelSerializer):
    """Serializer for Risk Action Notes."""
    
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = RiskActionNote
        fields = [
            'id', 'note', 'note_type', 'progress_percentage',
            'created_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = ['created_at', 'created_by']


class RiskActionEvidenceSerializer(serializers.ModelSerializer):
    """Serializer for Risk Action Evidence."""
    
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    validated_by_name = serializers.CharField(source='validated_by.get_full_name', read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = RiskActionEvidence
        fields = [
            'id', 'title', 'description', 'evidence_type', 
            'file', 'file_url', 'external_link',
            'is_validated', 'validated_by', 'validated_by_name', 
            'validated_at', 'validation_notes',
            'evidence_date', 'created_at', 'uploaded_by', 'uploaded_by_name'
        ]
        read_only_fields = [
            'created_at', 'uploaded_by', 'is_validated', 
            'validated_by', 'validated_at', 'validation_notes'
        ]

    def get_file_url(self, obj):
        """Get absolute URL for uploaded file."""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
        return None


class RiskActionListSerializer(serializers.ModelSerializer):
    """Serializer for Risk Action list view with essential fields."""
    
    risk_title = serializers.CharField(source='risk.title', read_only=True)
    risk_id = serializers.CharField(source='risk.risk_id', read_only=True)
    risk_level = serializers.CharField(source='risk.risk_level', read_only=True)
    risk_level_display = serializers.CharField(source='risk.get_risk_level_display', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    
    # Computed fields
    priority_color = serializers.CharField(source='get_priority_color', read_only=True)
    status_color = serializers.CharField(source='get_status_color', read_only=True)
    days_until_due = serializers.IntegerField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    is_due_soon = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = RiskAction
        fields = [
            'id', 'action_id', 'title', 'description', 'action_type',
            'risk', 'risk_id', 'risk_title', 'risk_level', 'risk_level_display',
            'assigned_to', 'assigned_to_name', 'status', 'priority',
            'priority_color', 'status_color', 'start_date', 'due_date',
            'completed_date', 'progress_percentage',
            'days_until_due', 'is_overdue', 'is_due_soon',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'action_id', 'days_until_due', 'is_overdue', 'is_due_soon',
            'created_at', 'updated_at', 'completed_date'
        ]


class RiskActionDetailSerializer(serializers.ModelSerializer):
    """Detailed Risk Action serializer with all fields and related data."""
    
    risk_title = serializers.CharField(source='risk.title', read_only=True)
    risk_id = serializers.CharField(source='risk.risk_id', read_only=True)
    risk_level = serializers.CharField(source='risk.risk_level', read_only=True)
    risk_level_display = serializers.CharField(source='risk.get_risk_level_display', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    # Computed fields
    priority_color = serializers.CharField(source='get_priority_color', read_only=True)
    status_color = serializers.CharField(source='get_status_color', read_only=True)
    days_until_due = serializers.IntegerField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    is_due_soon = serializers.BooleanField(read_only=True)
    
    # Related data
    risk_summary = serializers.SerializerMethodField()
    assigned_to = UserBasicSerializer(read_only=True)
    notes = RiskActionNoteSerializer(many=True, read_only=True)
    evidence = RiskActionEvidenceSerializer(many=True, read_only=True)
    
    class Meta:
        model = RiskAction
        fields = [
            'id', 'action_id', 'title', 'description', 'action_type',
            'risk', 'risk_id', 'risk_title', 'risk_level', 'risk_level_display', 'risk_summary',
            'assigned_to', 'assigned_to_name', 'status', 'priority',
            'priority_color', 'status_color', 'start_date', 'due_date', 'completed_date',
            'progress_percentage', 'estimated_cost', 'actual_cost', 'estimated_effort_hours',
            'success_criteria', 'dependencies',
            'days_until_due', 'is_overdue', 'is_due_soon',
            'created_at', 'updated_at', 'created_by', 'created_by_name',
            'notes', 'evidence'
        ]
        read_only_fields = [
            'action_id', 'days_until_due', 'is_overdue', 'is_due_soon',
            'created_at', 'updated_at', 'created_by', 'completed_date'
        ]

    def get_risk_summary(self, obj):
        """Get summary information about the related risk."""
        return {
            'id': obj.risk.id,
            'risk_id': obj.risk.risk_id,
            'title': obj.risk.title,
            'risk_level': obj.risk.risk_level,
            'risk_level_display': obj.risk.get_risk_level_display(),
            'status': obj.risk.status,
            'status_display': obj.risk.get_status_display(),
            'risk_owner': obj.risk.risk_owner.get_full_name() if obj.risk.risk_owner else None,
        }


class RiskActionCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating risk actions."""
    
    class Meta:
        model = RiskAction
        fields = [
            'risk', 'title', 'description', 'action_type', 'assigned_to',
            'priority', 'start_date', 'due_date', 'progress_percentage',
            'estimated_cost', 'actual_cost', 'estimated_effort_hours',
            'success_criteria', 'dependencies'
        ]

    def validate(self, data):
        """Cross-field validation."""
        # Validate date logic
        start_date = data.get('start_date')
        due_date = data.get('due_date')
        
        if start_date and due_date and start_date > due_date:
            raise serializers.ValidationError({
                'start_date': 'Start date cannot be after due date.'
            })
        
        # Validate progress percentage
        progress = data.get('progress_percentage', 0)
        if progress < 0 or progress > 100:
            raise serializers.ValidationError({
                'progress_percentage': 'Progress percentage must be between 0 and 100.'
            })
        
        return data

    def create(self, validated_data):
        """Create risk action with current user as creator."""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class RiskActionStatusUpdateSerializer(serializers.Serializer):
    """Serializer for updating risk action status with optional note."""
    
    status = serializers.ChoiceField(choices=RiskAction.STATUS_CHOICES)
    progress_percentage = serializers.IntegerField(min_value=0, max_value=100, required=False)
    note = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    
    def validate(self, data):
        """Cross-field validation for status updates."""
        status = data.get('status')
        progress = data.get('progress_percentage')
        
        # Auto-set progress to 100 for completed status
        if status == 'completed':
            data['progress_percentage'] = 100
        elif status == 'cancelled':
            # Don't require progress for cancelled actions
            pass
        
        return data
    
    def update_action_status(self, action):
        """Update action status and create note if provided."""
        from django.db import transaction
        from .notifications import RiskActionNotificationService
        
        old_status = action.status
        
        with transaction.atomic():
            # Update action fields
            action.status = self.validated_data['status']
            
            if 'progress_percentage' in self.validated_data:
                action.progress_percentage = self.validated_data['progress_percentage']
            
            action.save()
            
            # Create note if provided
            note_text = self.validated_data.get('note')
            if note_text:
                RiskActionNote.objects.create(
                    action=action,
                    note=note_text,
                    note_type='status_change',
                    progress_percentage=action.progress_percentage,
                    created_by=self.context['request'].user
                )
            
            # Send notification about status change
            RiskActionNotificationService.notify_status_change(
                action, old_status, action.status, self.context['request'].user
            )
        
        return action


class RiskActionNoteCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating risk action notes."""
    
    class Meta:
        model = RiskActionNote
        fields = ['note', 'note_type', 'progress_percentage']

    def create(self, validated_data):
        """Create note with current user as creator."""
        validated_data['created_by'] = self.context['request'].user
        validated_data['action'] = self.context['action']
        return super().create(validated_data)


class RiskActionEvidenceCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating risk action evidence."""
    
    class Meta:
        model = RiskActionEvidence
        fields = [
            'title', 'description', 'evidence_type', 'file',
            'external_link', 'evidence_date'
        ]

    def validate(self, data):
        """Validate that either file or external link is provided."""
        if not data.get('file') and not data.get('external_link'):
            raise serializers.ValidationError(
                "Either file or external link must be provided."
            )
        return data

    def create(self, validated_data):
        """Create evidence with current user as uploader."""
        from .notifications import RiskActionNotificationService
        
        validated_data['uploaded_by'] = self.context['request'].user
        validated_data['action'] = self.context['action']
        
        evidence = super().create(validated_data)
        
        # Send notification about evidence upload
        RiskActionNotificationService.notify_evidence_uploaded(
            evidence, self.context['request'].user
        )
        
        return evidence


class RiskActionBulkCreateSerializer(serializers.Serializer):
    """Serializer for bulk creating risk actions."""
    
    risk = serializers.PrimaryKeyRelatedField(queryset=Risk.objects.all())
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True
    )
    default_priority = serializers.ChoiceField(
        choices=RiskAction.PRIORITY_CHOICES,
        default='medium'
    )
    default_action_type = serializers.ChoiceField(
        choices=RiskAction.ACTION_TYPES,
        default='other'
    )
    
    actions = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        max_length=50,
        help_text='List of action dictionaries with title, description, and optional overrides'
    )
    
    def validate_actions(self, value):
        """Validate individual action data."""
        required_fields = ['title', 'description', 'due_date']
        
        for i, action_data in enumerate(value):
            # Check required fields
            for field in required_fields:
                if field not in action_data or not str(action_data[field]).strip():
                    raise serializers.ValidationError(
                        f"Action {i+1}: '{field}' is required and cannot be empty"
                    )
            
            # Validate due_date format
            try:
                from datetime import datetime
                if isinstance(action_data['due_date'], str):
                    datetime.strptime(action_data['due_date'], '%Y-%m-%d')
            except ValueError:
                raise serializers.ValidationError(
                    f"Action {i+1}: 'due_date' must be in YYYY-MM-DD format"
                )
        
        return value
    
    def create_bulk_actions(self):
        """Create multiple risk actions in bulk."""
        from django.db import transaction
        from .notifications import RiskActionReminderService
        
        created_actions = []
        errors = []
        
        with transaction.atomic():
            for i, action_data in enumerate(self.validated_data['actions']):
                try:
                    action = RiskAction.objects.create(
                        risk=self.validated_data['risk'],
                        title=action_data['title'],
                        description=action_data['description'],
                        action_type=action_data.get('action_type', self.validated_data['default_action_type']),
                        assigned_to=action_data.get('assigned_to') or self.validated_data.get('assigned_to'),
                        priority=action_data.get('priority', self.validated_data['default_priority']),
                        start_date=action_data.get('start_date'),
                        due_date=action_data['due_date'],
                        success_criteria=action_data.get('success_criteria', ''),
                        dependencies=action_data.get('dependencies', ''),
                        created_by=self.context['request'].user
                    )
                    created_actions.append(action)
                    
                    # Send assignment notification if user is assigned
                    if action.assigned_to:
                        RiskActionReminderService.send_assignment_notification(
                            action, action.assigned_to, self.context['request'].user
                        )
                    
                except Exception as e:
                    errors.append({
                        'index': i,
                        'title': action_data.get('title', ''),
                        'error': str(e)
                    })
        
        return created_actions, errors


class RiskActionSummarySerializer(serializers.Serializer):
    """Serializer for risk action summary statistics."""
    
    total_actions = serializers.IntegerField()
    by_status = serializers.DictField()
    by_priority = serializers.DictField()
    overdue_count = serializers.IntegerField()
    due_this_week = serializers.IntegerField()
    high_priority_pending = serializers.IntegerField()
    completion_rate = serializers.FloatField()
    
    # Top actions by category
    overdue_actions = RiskActionListSerializer(many=True, read_only=True)
    due_soon_actions = RiskActionListSerializer(many=True, read_only=True)
    high_priority_actions = RiskActionListSerializer(many=True, read_only=True)


class RiskActionReminderConfigurationSerializer(serializers.ModelSerializer):
    """Serializer for risk action reminder configuration."""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = RiskActionReminderConfiguration
        fields = [
            'id', 'user', 'user_name', 'enable_reminders', 'advance_warning_days',
            'reminder_frequency', 'custom_reminder_days', 'email_notifications',
            'overdue_reminders', 'weekly_digest_enabled', 'weekly_digest_day',
            'silence_completed', 'silence_cancelled', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']

    def validate_custom_reminder_days(self, value):
        """Validate custom reminder days when frequency is custom."""
        if self.instance and self.instance.reminder_frequency == 'custom':
            if not value or not isinstance(value, list):
                raise serializers.ValidationError(
                    "Custom reminder days must be a non-empty list when frequency is 'custom'."
                )
            if not all(isinstance(day, int) and day > 0 for day in value):
                raise serializers.ValidationError(
                    "All custom reminder days must be positive integers."
                )
        return value

    def validate_weekly_digest_day(self, value):
        """Validate weekly digest day is within valid range."""
        if value < 0 or value > 6:
            raise serializers.ValidationError(
                "Weekly digest day must be between 0 (Monday) and 6 (Sunday)."
            )
        return value