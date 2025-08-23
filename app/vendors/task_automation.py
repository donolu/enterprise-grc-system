"""
Vendor Task Automation System

Automatically generates vendor tasks based on contract dates, compliance requirements,
and other vendor-related schedules. Integrates with existing contract management.
"""

from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class VendorTaskAutomationService:
    """
    Service for automatically generating vendor tasks based on contract dates
    and compliance requirements.
    """
    
    def __init__(self):
        self.default_reminder_days = [30, 14, 7, 1]
    
    def generate_contract_renewal_tasks(self, vendor=None) -> int:
        """
        Generate contract renewal tasks for vendors with upcoming contract expirations.
        
        Args:
            vendor: Optional specific vendor to process (defaults to all vendors)
            
        Returns:
            int: Number of tasks created
        """
        from .models import Vendor, VendorTask
        
        # Get vendors with contract end dates
        vendors_query = Vendor.objects.exclude(contract_end_date__isnull=True)
        if vendor:
            vendors_query = vendors_query.filter(id=vendor.id)
        
        tasks_created = 0
        
        for vendor_obj in vendors_query:
            # Skip if task already exists for this contract
            existing_task = VendorTask.objects.filter(
                vendor=vendor_obj,
                task_type='contract_renewal',
                related_contract_number=vendor_obj.primary_contract_number,
                status__in=['pending', 'in_progress']
            ).first()
            
            if existing_task:
                continue
            
            # Calculate task due date (renewal notice days before contract end)
            notice_days = vendor_obj.renewal_notice_days or 90
            task_due_date = vendor_obj.contract_end_date - timedelta(days=notice_days)
            
            # Only create task if due date is in the future or within 30 days past
            if task_due_date < (timezone.now().date() - timedelta(days=30)):
                continue
            
            # Create contract renewal task
            task = VendorTask.objects.create(
                vendor=vendor_obj,
                task_type='contract_renewal',
                title=f"Contract Renewal - {vendor_obj.name}",
                description=self._generate_contract_renewal_description(vendor_obj),
                due_date=task_due_date,
                priority='high' if notice_days <= 30 else 'medium',
                assigned_to=vendor_obj.assigned_to,
                reminder_days=self._get_reminder_schedule('contract_renewal', notice_days),
                related_contract_number=vendor_obj.primary_contract_number,
                auto_generated=True,
                generation_source='contract_expiry',
                created_by=self._get_system_user()
            )
            
            tasks_created += 1
            logger.info(f"Created contract renewal task {task.task_id} for {vendor_obj.name}")
        
        return tasks_created
    
    def generate_security_review_tasks(self, vendor=None) -> int:
        """
        Generate security review tasks for vendors based on their risk level and last review date.
        
        Args:
            vendor: Optional specific vendor to process
            
        Returns:
            int: Number of tasks created
        """
        from .models import Vendor, VendorTask
        
        vendors_query = Vendor.objects.filter(status='active')
        if vendor:
            vendors_query = vendors_query.filter(id=vendor.id)
        
        tasks_created = 0
        
        for vendor_obj in vendors_query:
            # Determine review frequency based on risk level
            review_frequency_days = self._get_security_review_frequency(vendor_obj.risk_level)
            
            # Calculate next review date
            last_review = vendor_obj.security_assessment_date or vendor_obj.relationship_start_date
            if not last_review:
                continue
            
            next_review_date = last_review + timedelta(days=review_frequency_days)
            
            # Skip if review is not due within next 60 days
            if next_review_date > (timezone.now().date() + timedelta(days=60)):
                continue
            
            # Check if task already exists
            existing_task = VendorTask.objects.filter(
                vendor=vendor_obj,
                task_type='security_review',
                due_date__gte=next_review_date - timedelta(days=30),
                status__in=['pending', 'in_progress']
            ).first()
            
            if existing_task:
                continue
            
            # Create security review task
            task = VendorTask.objects.create(
                vendor=vendor_obj,
                task_type='security_review',
                title=f"Security Assessment - {vendor_obj.name}",
                description=self._generate_security_review_description(vendor_obj),
                due_date=next_review_date,
                priority=self._get_priority_for_risk_level(vendor_obj.risk_level),
                assigned_to=vendor_obj.assigned_to,
                reminder_days=self._get_reminder_schedule('security_review'),
                auto_generated=True,
                generation_source='security_schedule',
                created_by=self._get_system_user()
            )
            
            tasks_created += 1
            logger.info(f"Created security review task {task.task_id} for {vendor_obj.name}")
        
        return tasks_created
    
    def generate_compliance_assessment_tasks(self, vendor=None) -> int:
        """
        Generate compliance assessment tasks based on vendor categories and regional requirements.
        
        Args:
            vendor: Optional specific vendor to process
            
        Returns:
            int: Number of tasks created
        """
        from .models import Vendor, VendorTask
        
        vendors_query = Vendor.objects.filter(
            status='active',
            category__isnull=False
        ).select_related('category')
        
        if vendor:
            vendors_query = vendors_query.filter(id=vendor.id)
        
        tasks_created = 0
        
        for vendor_obj in vendors_query:
            # Check if vendor requires regular compliance assessments
            if not vendor_obj.data_processing_agreement and vendor_obj.risk_level in ['high', 'critical']:
                # Create DPA review task
                task = VendorTask.objects.create(
                    vendor=vendor_obj,
                    task_type='data_processing_agreement',
                    title=f"Data Processing Agreement Review - {vendor_obj.name}",
                    description=self._generate_dpa_review_description(vendor_obj),
                    due_date=timezone.now().date() + timedelta(days=30),
                    priority='high',
                    assigned_to=vendor_obj.assigned_to,
                    reminder_days=[14, 7, 3, 1],
                    auto_generated=True,
                    generation_source='compliance_check',
                    created_by=self._get_system_user()
                )
                
                tasks_created += 1
                logger.info(f"Created DPA review task {task.task_id} for {vendor_obj.name}")
            
            # Generate annual compliance review for high-risk vendors
            if vendor_obj.risk_level in ['high', 'critical']:
                existing_task = VendorTask.objects.filter(
                    vendor=vendor_obj,
                    task_type='compliance_assessment',
                    due_date__gte=timezone.now().date(),
                    status__in=['pending', 'in_progress']
                ).first()
                
                if not existing_task:
                    task = VendorTask.objects.create(
                        vendor=vendor_obj,
                        task_type='compliance_assessment',
                        title=f"Annual Compliance Assessment - {vendor_obj.name}",
                        description=self._generate_compliance_assessment_description(vendor_obj),
                        due_date=timezone.now().date() + timedelta(days=90),
                        priority='medium',
                        assigned_to=vendor_obj.assigned_to,
                        reminder_days=self._get_reminder_schedule('compliance_assessment'),
                        auto_generated=True,
                        generation_source='compliance_schedule',
                        created_by=self._get_system_user()
                    )
                    
                    tasks_created += 1
                    logger.info(f"Created compliance assessment task {task.task_id} for {vendor_obj.name}")
        
        return tasks_created
    
    def generate_performance_review_tasks(self, vendor=None) -> int:
        """
        Generate performance review tasks for vendors based on their contract terms.
        
        Args:
            vendor: Optional specific vendor to process
            
        Returns:
            int: Number of tasks created
        """
        from .models import Vendor, VendorTask
        
        vendors_query = Vendor.objects.filter(
            status='active',
            annual_spend__gte=10000  # Only for vendors with significant spend
        )
        
        if vendor:
            vendors_query = vendors_query.filter(id=vendor.id)
        
        tasks_created = 0
        
        for vendor_obj in vendors_query:
            # Determine review frequency based on spend and risk
            if vendor_obj.annual_spend and vendor_obj.annual_spend >= 100000:
                review_frequency = 180  # Every 6 months for high-spend vendors
            else:
                review_frequency = 365  # Annual for others
            
            # Calculate next review date
            last_review = vendor_obj.last_performance_review or vendor_obj.relationship_start_date
            if not last_review:
                continue
            
            next_review_date = last_review + timedelta(days=review_frequency)
            
            # Skip if not due within next 30 days
            if next_review_date > (timezone.now().date() + timedelta(days=30)):
                continue
            
            # Check for existing task
            existing_task = VendorTask.objects.filter(
                vendor=vendor_obj,
                task_type='performance_review',
                due_date__gte=next_review_date - timedelta(days=60),
                status__in=['pending', 'in_progress']
            ).first()
            
            if existing_task:
                continue
            
            # Create performance review task
            task = VendorTask.objects.create(
                vendor=vendor_obj,
                task_type='performance_review',
                title=f"Performance Review - {vendor_obj.name}",
                description=self._generate_performance_review_description(vendor_obj),
                due_date=next_review_date,
                priority='medium',
                assigned_to=vendor_obj.assigned_to,
                reminder_days=self._get_reminder_schedule('performance_review'),
                auto_generated=True,
                generation_source='performance_schedule',
                created_by=self._get_system_user()
            )
            
            tasks_created += 1
            logger.info(f"Created performance review task {task.task_id} for {vendor_obj.name}")
        
        return tasks_created
    
    def run_daily_automation(self) -> Dict[str, int]:
        """
        Run daily automation to generate all types of vendor tasks.
        
        Returns:
            dict: Summary of tasks created by type
        """
        logger.info("Starting daily vendor task automation")
        
        results = {
            'contract_renewals': self.generate_contract_renewal_tasks(),
            'security_reviews': self.generate_security_review_tasks(),
            'compliance_assessments': self.generate_compliance_assessment_tasks(),
            'performance_reviews': self.generate_performance_review_tasks(),
        }
        
        total_created = sum(results.values())
        logger.info(f"Daily automation completed: {total_created} tasks created")
        
        return results
    
    def _generate_contract_renewal_description(self, vendor) -> str:
        """Generate description for contract renewal task."""
        return f"""
Contract for {vendor.name} expires on {vendor.contract_end_date.strftime('%B %d, %Y')}.

Action Items:
1. Review current contract terms and performance
2. Assess need for renewal vs. replacement
3. Negotiate renewal terms if proceeding
4. Obtain necessary approvals
5. Execute renewed contract

Contract Details:
- Contract Number: {vendor.primary_contract_number or 'Not specified'}
- Annual Spend: ${vendor.annual_spend:,.2f} if vendor.annual_spend else 'Not specified'
- Auto-Renewal: {'Yes' if vendor.auto_renewal else 'No'}
- Notice Period: {vendor.renewal_notice_days} days

Key Contacts: Review vendor contacts for renewal discussions.
"""
    
    def _generate_security_review_description(self, vendor) -> str:
        """Generate description for security review task."""
        last_review = vendor.security_assessment_date.strftime('%B %d, %Y') if vendor.security_assessment_date else 'Never'
        
        return f"""
Security assessment required for {vendor.name} (Risk Level: {vendor.get_risk_level_display()}).

Last Assessment: {last_review}

Review Items:
1. Security controls and policies
2. Data handling practices
3. Incident response capabilities
4. Compliance certifications (ISO 27001, SOC 2, etc.)
5. Third-party security assessments

Risk Level: {vendor.get_risk_level_display()}
Data Processing Agreement: {'In place' if vendor.data_processing_agreement else 'Required'}

Services Provided: {', '.join([s.service_name for s in vendor.services.all()[:3]])}
"""
    
    def _generate_dpa_review_description(self, vendor) -> str:
        """Generate description for DPA review task."""
        return f"""
Data Processing Agreement (DPA) review required for {vendor.name}.

Current Status: {'DPA in place' if vendor.data_processing_agreement else 'No DPA on file'}
Risk Level: {vendor.get_risk_level_display()}

Action Items:
1. Review data processing activities with this vendor
2. Assess legal basis for data processing
3. Ensure appropriate safeguards are in place
4. Execute DPA if required
5. Update vendor records

Operating Regions: {', '.join(vendor.operating_regions) if vendor.operating_regions else 'Not specified'}
"""
    
    def _generate_compliance_assessment_description(self, vendor) -> str:
        """Generate description for compliance assessment task."""
        return f"""
Annual compliance assessment for {vendor.name}.

Risk Level: {vendor.get_risk_level_display()}
Category: {vendor.category.name if vendor.category else 'Not categorized'}

Assessment Areas:
1. Regulatory compliance requirements
2. Industry standards adherence
3. Contractual compliance
4. Data protection compliance
5. Financial and operational compliance

Certifications: {', '.join(vendor.certifications) if vendor.certifications else 'None on file'}
Operating Regions: {', '.join(vendor.operating_regions) if vendor.operating_regions else 'Not specified'}
"""
    
    def _generate_performance_review_description(self, vendor) -> str:
        """Generate description for performance review task."""
        last_review = vendor.last_performance_review.strftime('%B %d, %Y') if vendor.last_performance_review else 'Never'
        
        return f"""
Performance review for {vendor.name}.

Last Review: {last_review}
Annual Spend: ${vendor.annual_spend:,.2f} if vendor.annual_spend else 'Not specified'
Current Score: {vendor.performance_score}/100 if vendor.performance_score else 'Not scored'

Review Areas:
1. Service delivery quality
2. SLA compliance
3. Cost effectiveness
4. Relationship management
5. Innovation and value-add
6. Risk management

Services: {vendor.services.count()} active service{'s' if vendor.services.count() != 1 else ''}
"""
    
    def _get_security_review_frequency(self, risk_level: str) -> int:
        """Get security review frequency in days based on risk level."""
        frequencies = {
            'critical': 90,    # Every 3 months
            'high': 180,       # Every 6 months
            'medium': 365,     # Annually
            'low': 730,        # Every 2 years
        }
        return frequencies.get(risk_level, 365)
    
    def _get_priority_for_risk_level(self, risk_level: str) -> str:
        """Get task priority based on vendor risk level."""
        priorities = {
            'critical': 'critical',
            'high': 'high',
            'medium': 'medium',
            'low': 'low',
        }
        return priorities.get(risk_level, 'medium')
    
    def _get_reminder_schedule(self, task_type: str, notice_days: int = None) -> List[int]:
        """Get reminder schedule based on task type and notice period."""
        if task_type == 'contract_renewal' and notice_days:
            if notice_days >= 90:
                return [60, 30, 14, 7, 1]
            elif notice_days >= 30:
                return [14, 7, 3, 1]
            else:
                return [7, 3, 1]
        
        schedules = {
            'security_review': [30, 14, 7, 1],
            'compliance_assessment': [30, 14, 7, 1],
            'performance_review': [14, 7, 1],
            'data_processing_agreement': [14, 7, 3, 1],
        }
        
        return schedules.get(task_type, self.default_reminder_days)
    
    def _get_system_user(self) -> Optional[User]:
        """Get system user for auto-generated tasks."""
        try:
            # Try to get a system user or fallback to first superuser
            system_user = User.objects.filter(
                username__in=['system', 'automation', 'admin'],
                is_active=True
            ).first()
            
            if not system_user:
                system_user = User.objects.filter(is_superuser=True, is_active=True).first()
            
            return system_user
        except Exception:
            return None


def get_automation_service() -> VendorTaskAutomationService:
    """Factory function to get automation service instance."""
    return VendorTaskAutomationService()


def run_daily_task_generation() -> Dict[str, Any]:
    """
    Daily function to generate vendor tasks automatically.
    Designed to be called by a scheduled task/cron job.
    
    Returns:
        dict: Summary of task generation results
    """
    automation_service = get_automation_service()
    results = automation_service.run_daily_automation()
    
    return {
        'status': 'success',
        'message': f"Generated {sum(results.values())} tasks",
        'breakdown': results
    }