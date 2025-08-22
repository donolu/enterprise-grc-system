from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class LimitOverrideNotificationService:
    """
    Service for sending notifications related to limit override requests.
    """
    
    @staticmethod
    def get_approver_emails():
        """
        Get list of approver email addresses.
        In a real implementation, this would query users with approval permissions.
        """
        # TODO: Implement based on your user/permission system
        # For now, return admin emails from settings or hard-coded for demo
        return getattr(settings, 'LIMIT_OVERRIDE_APPROVER_EMAILS', [
            'admin@example.com',  # Replace with actual approver emails
        ])
    
    @staticmethod
    def send_new_request_notification(override_request):
        """Send notification when a new override request is created."""
        try:
            approver_emails = LimitOverrideNotificationService.get_approver_emails()
            
            if not approver_emails:
                logger.warning("No approver emails configured for limit override notifications")
                return
            
            subject = f"New Limit Override Request - {override_request.subscription.tenant.name}"
            
            context = {
                'override_request': override_request,
                'tenant_name': override_request.subscription.tenant.name,
                'limit_type': override_request.get_limit_type_display(),
                'current_limit': override_request.current_limit,
                'requested_limit': override_request.requested_limit,
                'urgency': override_request.get_urgency_display(),
                'justification': override_request.business_justification,
                'requested_by': override_request.requested_by,
                'requested_at': override_request.requested_at,
                'approval_url': f"{settings.SITE_DOMAIN}/admin/limit-overrides/{override_request.id}/"
            }
            
            # Plain text email (you could also create HTML template)
            message = f"""
A new limit override request has been submitted and requires approval.

Tenant: {override_request.subscription.tenant.name}
Limit Type: {override_request.get_limit_type_display()}
Current Limit: {override_request.current_limit}
Requested Limit: {override_request.requested_limit}
Urgency: {override_request.get_urgency_display()}
Requested By: {override_request.requested_by}
Requested At: {override_request.requested_at}

Business Justification:
{override_request.business_justification}

Please review and provide approval at: {context['approval_url']}

This request requires TWO approvals before it can be applied.
            """.strip()
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=approver_emails,
                fail_silently=False
            )
            
            logger.info(f"Sent new request notification for override {override_request.id}")
            
        except Exception as e:
            logger.error(f"Failed to send new request notification: {str(e)}")
    
    @staticmethod
    def send_first_approval_notification(override_request):
        """Send notification when first approval is received."""
        try:
            approver_emails = LimitOverrideNotificationService.get_approver_emails()
            
            subject = f"First Approval Received - {override_request.subscription.tenant.name} Override Request"
            
            message = f"""
The limit override request has received its FIRST approval and now needs a SECOND approval.

Tenant: {override_request.subscription.tenant.name}
Limit Type: {override_request.get_limit_type_display()}
Current Limit: {override_request.current_limit}
Requested Limit: {override_request.requested_limit}

First Approved By: {override_request.first_approver}
First Approved At: {override_request.first_approved_at}
First Approval Notes: {override_request.first_approval_notes or 'None'}

⚠️  This request now needs a SECOND approval from a different person.

Please review and provide second approval at: {settings.SITE_DOMAIN}/admin/limit-overrides/{override_request.id}/
            """.strip()
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=approver_emails,
                fail_silently=False
            )
            
            logger.info(f"Sent first approval notification for override {override_request.id}")
            
        except Exception as e:
            logger.error(f"Failed to send first approval notification: {str(e)}")
    
    @staticmethod
    def send_final_approval_notification(override_request):
        """Send notification when request is fully approved."""
        try:
            # Notify both approvers and admins who can apply the override
            approver_emails = LimitOverrideNotificationService.get_approver_emails()
            admin_emails = getattr(settings, 'ADMIN_NOTIFICATION_EMAILS', approver_emails)
            
            all_emails = list(set(approver_emails + admin_emails))
            
            subject = f"APPROVED - {override_request.subscription.tenant.name} Override Request Ready to Apply"
            
            message = f"""
✅ The limit override request has been FULLY APPROVED and is ready to be applied.

Tenant: {override_request.subscription.tenant.name}
Limit Type: {override_request.get_limit_type_display()}
Current Limit: {override_request.current_limit}
Requested Limit: {override_request.requested_limit}

First Approved By: {override_request.first_approver}
Second Approved By: {override_request.second_approver}
Final Decision At: {override_request.final_decision_at}

⚠️  An administrator needs to apply this override to activate the new limits.

Apply override at: {settings.SITE_DOMAIN}/admin/limit-overrides/{override_request.id}/apply/
            """.strip()
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=all_emails,
                fail_silently=False
            )
            
            logger.info(f"Sent final approval notification for override {override_request.id}")
            
        except Exception as e:
            logger.error(f"Failed to send final approval notification: {str(e)}")
    
    @staticmethod
    def send_rejection_notification(override_request):
        """Send notification when request is rejected."""
        try:
            # Notify the requester (you'd need to implement getting requester email)
            # For now, just log it
            
            subject = f"REJECTED - {override_request.subscription.tenant.name} Override Request"
            
            message = f"""
❌ The limit override request has been REJECTED.

Tenant: {override_request.subscription.tenant.name}
Limit Type: {override_request.get_limit_type_display()}
Requested Limit: {override_request.requested_limit}

Rejected By: {override_request.final_decision_by}
Rejected At: {override_request.final_decision_at}
Rejection Reason: {override_request.rejection_reason}

If you have questions about this rejection, please contact the approver team.
            """.strip()
            
            logger.info(f"Override request {override_request.id} was rejected: {override_request.rejection_reason}")
            
            # TODO: Send to requester email when user system is integrated
            
        except Exception as e:
            logger.error(f"Failed to send rejection notification: {str(e)}")
    
    @staticmethod
    def send_application_notification(override_request):
        """Send notification when override is applied."""
        try:
            # Notify relevant parties that the override has been applied
            approver_emails = LimitOverrideNotificationService.get_approver_emails()
            
            subject = f"APPLIED - {override_request.subscription.tenant.name} Override is Now Active"
            
            message = f"""
🎉 The limit override has been SUCCESSFULLY APPLIED.

Tenant: {override_request.subscription.tenant.name}
Limit Type: {override_request.get_limit_type_display()}
Previous Limit: {override_request.current_limit}
New Limit: {override_request.requested_limit}

Applied By: {override_request.applied_by}
Applied At: {override_request.applied_at}

The new limits are now active for this tenant.
            """.strip()
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=approver_emails,
                fail_silently=False
            )
            
            logger.info(f"Sent application notification for override {override_request.id}")
            
        except Exception as e:
            logger.error(f"Failed to send application notification: {str(e)}")