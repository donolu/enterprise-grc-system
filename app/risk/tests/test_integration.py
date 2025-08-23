from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core import mail
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock

from ..models import (
    Risk, RiskCategory, RiskAction, RiskActionNote, 
    RiskActionEvidence, RiskActionReminderConfiguration, RiskActionReminderLog
)
from ..notifications import RiskActionReminderService, RiskActionNotificationService
from ..tasks import send_risk_action_due_reminders, send_risk_action_weekly_digests

User = get_user_model()


class RiskActionWorkflowIntegrationTest(APITestCase):
    """Integration tests for complete risk action workflows."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='workflow_user',
            email='workflow@example.com',
            first_name='Workflow',
            last_name='User',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.category = RiskCategory.objects.create(
            name='Integration Test Category',
            code='INTEG'
        )
        self.risk = Risk.objects.create(
            title='Integration Test Risk',
            description='Risk for integration testing',
            category=self.category,
            risk_owner=self.user,
            impact=4,
            likelihood=3,
            risk_level='high',
            status='assessed'
        )
        
        # Ensure user has notification configuration
        RiskActionReminderConfiguration.objects.create(
            user=self.user,
            enabled=True,
            send_assignment_notifications=True,
            send_status_change_notifications=True,
            send_evidence_notifications=True,
            send_due_reminders=True,
            send_overdue_reminders=True,
            send_weekly_digest=True,
            reminder_days_before=7
        )
    
    def test_complete_risk_action_lifecycle(self):
        """Test complete lifecycle from creation to completion."""
        # Step 1: Create risk action via API
        create_url = reverse('riskaction-list')
        create_data = {
            'risk': self.risk.id,
            'title': 'Complete Lifecycle Action',
            'description': 'Action to test complete lifecycle',
            'action_type': 'mitigation',
            'priority': 'high',
            'assigned_to': self.user.id,
            'due_date': (date.today() + timedelta(days=30)).isoformat(),
            'start_date': date.today().isoformat()
        }
        
        with patch('risk.notifications.RiskActionNotificationService.notify_assignment') as mock_notify:
            response = self.client.post(create_url, create_data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            action_id = response.data['id']
            
            # Should trigger assignment notification
            mock_notify.assert_called_once()
        
        # Step 2: Add note to action
        note_url = reverse('riskaction-add-note', kwargs={'pk': action_id})
        note_data = {'note': 'Starting work on this action'}
        
        response = self.client.post(note_url, note_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify note was created
        action = RiskAction.objects.get(id=action_id)
        self.assertEqual(action.notes.count(), 1)
        self.assertEqual(action.notes.first().note, 'Starting work on this action')
        
        # Step 3: Update status to in_progress
        status_url = reverse('riskaction-update-status', kwargs={'pk': action_id})
        status_data = {
            'status': 'in_progress',
            'progress_percentage': 25,
            'note': 'Made initial progress on action'
        }
        
        with patch('risk.notifications.RiskActionNotificationService.notify_status_change') as mock_notify:
            response = self.client.post(status_url, status_data, format='json')
            
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            # Should trigger status change notification
            mock_notify.assert_called_once()
        
        # Verify status update
        action.refresh_from_db()
        self.assertEqual(action.status, 'in_progress')
        self.assertEqual(action.progress_percentage, 25)
        self.assertEqual(action.notes.count(), 2)  # Original note + status update note
        
        # Step 4: Upload evidence
        evidence_url = reverse('riskaction-upload-evidence', kwargs={'pk': action_id})
        evidence_data = {
            'title': 'Progress Evidence',
            'evidence_type': 'document',
            'description': 'Evidence of progress made',
            'external_link': 'https://example.com/evidence-doc'
        }
        
        with patch('risk.notifications.RiskActionNotificationService.notify_evidence_uploaded') as mock_notify:
            response = self.client.post(evidence_url, evidence_data, format='multipart')
            
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            # Should trigger evidence notification
            mock_notify.assert_called_once()
        
        # Verify evidence was created
        self.assertEqual(action.evidence.count(), 1)
        evidence = action.evidence.first()
        self.assertEqual(evidence.title, 'Progress Evidence')
        self.assertEqual(evidence.uploaded_by, self.user)
        
        # Step 5: Update progress
        progress_data = {
            'status': 'in_progress',
            'progress_percentage': 75,
            'note': 'Significant progress made'
        }
        
        response = self.client.post(status_url, progress_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        action.refresh_from_db()
        self.assertEqual(action.progress_percentage, 75)
        
        # Step 6: Complete the action
        completion_data = {
            'status': 'completed',
            'progress_percentage': 100,
            'note': 'Action completed successfully'
        }
        
        response = self.client.post(status_url, completion_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        action.refresh_from_db()
        self.assertEqual(action.status, 'completed')
        self.assertEqual(action.progress_percentage, 100)
        self.assertIsNotNone(action.completed_date)
        
        # Verify final state
        self.assertEqual(action.notes.count(), 4)  # All status update notes
        self.assertEqual(action.evidence.count(), 1)
        self.assertTrue(action.is_completed)
    
    def test_risk_action_filtering_integration(self):
        """Test comprehensive filtering functionality."""
        # Create various actions with different attributes
        actions_data = [
            {
                'title': 'High Priority Overdue',
                'priority': 'high',
                'due_date': date.today() - timedelta(days=2),
                'status': 'in_progress'
            },
            {
                'title': 'Medium Priority Due Soon',
                'priority': 'medium',
                'due_date': date.today() + timedelta(days=3),
                'status': 'pending'
            },
            {
                'title': 'Low Priority Future',
                'priority': 'low',
                'due_date': date.today() + timedelta(days=30),
                'status': 'pending'
            },
            {
                'title': 'Completed High Priority',
                'priority': 'high',
                'due_date': date.today() - timedelta(days=5),
                'status': 'completed'
            }
        ]
        
        created_actions = []
        for action_data in actions_data:
            action = RiskAction.objects.create(
                risk=self.risk,
                action_type='mitigation',
                assigned_to=self.user,
                **action_data
            )
            created_actions.append(action)
        
        base_url = reverse('riskaction-list')
        
        # Test overdue filter
        response = self.client.get(f'{base_url}?overdue=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'High Priority Overdue')
        
        # Test due soon filter
        response = self.client.get(f'{base_url}?due_soon=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Medium Priority Due Soon')
        
        # Test high priority filter
        response = self.client.get(f'{base_url}?high_priority=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        
        # Test active only filter (excludes completed)
        response = self.client.get(f'{base_url}?active_only=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)
        
        # Test assigned to me filter
        response = self.client.get(f'{base_url}?assigned_to_me=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 4)  # All assigned to current user
        
        # Test search filter
        response = self.client.get(f'{base_url}?search=Due Soon')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Medium Priority Due Soon')
        
        # Test combined filters
        response = self.client.get(f'{base_url}?high_priority=true&active_only=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)  # Only active high priority
        self.assertEqual(response.data['results'][0]['title'], 'High Priority Overdue')
    
    def test_reminder_system_integration(self):
        """Test complete reminder system integration."""
        # Create actions with different reminder scenarios
        actions = [
            RiskAction.objects.create(
                risk=self.risk,
                title='Due in 7 Days',
                action_type='mitigation',
                assigned_to=self.user,
                due_date=date.today() + timedelta(days=7),
                status='pending'
            ),
            RiskAction.objects.create(
                risk=self.risk,
                title='Due Today',
                action_type='mitigation',
                assigned_to=self.user,
                due_date=date.today(),
                status='in_progress'
            ),
            RiskAction.objects.create(
                risk=self.risk,
                title='Overdue',
                action_type='acceptance',
                assigned_to=self.user,
                due_date=date.today() - timedelta(days=2),
                status='pending'
            )
        ]
        
        with patch('risk.notifications.send_mail') as mock_send_mail:
            mock_send_mail.return_value = True
            
            # Run the reminder task
            result = send_risk_action_due_reminders.apply()
            
            self.assertTrue(result.successful())
            # Should send reminders for all three actions
            self.assertEqual(mock_send_mail.call_count, 3)
            
            # Verify reminder logs were created
            for action in actions:
                log_exists = RiskActionReminderLog.objects.filter(
                    action=action,
                    user=self.user
                ).exists()
                self.assertTrue(log_exists)
    
    def test_weekly_digest_integration(self):
        """Test weekly digest functionality."""
        # Create various actions for the user
        RiskAction.objects.create(
            risk=self.risk,
            title='Pending Action',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=5),
            status='pending'
        )
        RiskAction.objects.create(
            risk=self.risk,
            title='In Progress Action',
            action_type='acceptance',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=10),
            status='in_progress',
            progress_percentage=50
        )
        RiskAction.objects.create(
            risk=self.risk,
            title='Completed Action',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() - timedelta(days=3),
            status='completed',
            completed_date=date.today() - timedelta(days=1)
        )
        
        with patch('risk.notifications.send_mail') as mock_send_mail:
            mock_send_mail.return_value = True
            
            # Run weekly digest task
            result = send_risk_action_weekly_digests.apply()
            
            self.assertTrue(result.successful())
            # Should send digest to user
            mock_send_mail.assert_called_once()
            
            # Verify email content structure
            call_args = mock_send_mail.call_args
            email_subject = call_args[0][0]
            email_body = call_args[0][1]
            
            self.assertIn('Weekly Risk Action Digest', email_subject)
            self.assertIn(self.user.email, call_args[0][3])
            
            # Check that actions are included in digest
            self.assertIn('Pending Action', email_body)
            self.assertIn('In Progress Action', email_body)
    
    def test_error_handling_integration(self):
        """Test error handling across the system."""
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Error Test Action',
            action_type='mitigation',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=14)
        )
        
        # Test API error handling with invalid data
        status_url = reverse('riskaction-update-status', kwargs={'pk': action.id})
        invalid_data = {
            'status': 'invalid_status',
            'progress_percentage': 150,  # Invalid percentage
        }
        
        response = self.client.post(status_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)
        
        # Test notification error handling
        with patch('risk.notifications.send_mail', side_effect=Exception('SMTP Error')):
            # Should not raise exception, just log error
            result = RiskActionNotificationService.notify_assignment(action, self.user)
            self.assertFalse(result)
        
        # Test task error handling
        with patch('risk.models.User.objects.filter', side_effect=Exception('DB Error')):
            # Task should handle error gracefully
            result = send_risk_action_due_reminders.apply()
            self.assertTrue(result.successful())  # Should not fail the task
    
    def test_permissions_integration(self):
        """Test permission handling across different endpoints."""
        # Create another user without access
        other_user = User.objects.create_user(
            username='other_user',
            email='other@example.com',
            password='testpass123'
        )
        
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Permission Test Action',
            action_type='mitigation',
            assigned_to=self.user,  # Assigned to authenticated user
            due_date=date.today() + timedelta(days=14)
        )
        
        # Switch to other user
        self.client.force_authenticate(user=other_user)
        
        # Test read access (should be allowed)
        list_url = reverse('riskaction-list')
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Test update access
        status_url = reverse('riskaction-update-status', kwargs={'pk': action.id})
        status_data = {'status': 'in_progress', 'progress_percentage': 25}
        
        response = self.client.post(status_url, status_data, format='json')
        # Should be allowed (basic implementation allows updates)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN])
        
        # Test creation access
        create_url = reverse('riskaction-list')
        create_data = {
            'risk': self.risk.id,
            'title': 'Unauthorized Action',
            'action_type': 'mitigation',
            'assigned_to': other_user.id,
            'due_date': (date.today() + timedelta(days=30)).isoformat()
        }
        
        response = self.client.post(create_url, create_data, format='json')
        # Should be allowed for basic case
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_403_FORBIDDEN])
    
    def test_data_consistency_integration(self):
        """Test data consistency across related models."""
        action = RiskAction.objects.create(
            risk=self.risk,
            title='Consistency Test Action',
            description='Testing data consistency',
            action_type='mitigation',
            priority='high',
            assigned_to=self.user,
            due_date=date.today() + timedelta(days=30),
            status='pending'
        )
        
        # Add multiple notes
        notes_data = [
            'First note about the action',
            'Second note with more details',
            'Third note with progress update'
        ]
        
        for note_text in notes_data:
            RiskActionNote.objects.create(
                action=action,
                note=note_text,
                created_by=self.user
            )
        
        # Add multiple evidence items
        evidence_data = [
            {'title': 'Document Evidence', 'evidence_type': 'document'},
            {'title': 'Screenshot Evidence', 'evidence_type': 'screenshot'},
            {'title': 'Link Evidence', 'evidence_type': 'link'}
        ]
        
        for evidence_item in evidence_data:
            RiskActionEvidence.objects.create(
                action=action,
                uploaded_by=self.user,
                **evidence_item
            )
        
        # Verify relationships
        self.assertEqual(action.notes.count(), 3)
        self.assertEqual(action.evidence.count(), 3)
        
        # Test cascade behavior (if implemented)
        action_id = action.id
        
        # Delete the action and verify related objects
        action.delete()
        
        # Notes and evidence should be deleted (if cascade is set up)
        remaining_notes = RiskActionNote.objects.filter(action_id=action_id)
        remaining_evidence = RiskActionEvidence.objects.filter(action_id=action_id)
        
        self.assertEqual(remaining_notes.count(), 0)
        self.assertEqual(remaining_evidence.count(), 0)
    
    def test_performance_integration(self):
        """Test system performance with realistic data volumes."""
        # Create a reasonable number of actions for performance testing
        actions = []
        for i in range(20):
            action = RiskAction.objects.create(
                risk=self.risk,
                title=f'Performance Action {i}',
                description=f'Action {i} for performance testing',
                action_type='mitigation',
                priority=['low', 'medium', 'high'][i % 3],
                assigned_to=self.user,
                due_date=date.today() + timedelta(days=i),
                status=['pending', 'in_progress'][i % 2]
            )
            actions.append(action)
            
            # Add notes to some actions
            if i % 3 == 0:
                RiskActionNote.objects.create(
                    action=action,
                    note=f'Note for action {i}',
                    created_by=self.user
                )
            
            # Add evidence to some actions
            if i % 4 == 0:
                RiskActionEvidence.objects.create(
                    action=action,
                    title=f'Evidence for action {i}',
                    evidence_type='document',
                    uploaded_by=self.user
                )
        
        # Test API performance
        start_time = timezone.now()
        
        # List all actions
        list_url = reverse('riskaction-list')
        response = self.client.get(list_url)
        
        end_time = timezone.now()
        response_time = (end_time - start_time).total_seconds()
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 20)
        # Should respond within reasonable time
        self.assertLess(response_time, 2.0)  # 2 seconds max
        
        # Test filtered queries
        start_time = timezone.now()
        
        response = self.client.get(f'{list_url}?high_priority=true&active_only=true')
        
        end_time = timezone.now()
        filter_time = (end_time - start_time).total_seconds()
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(filter_time, 1.0)  # 1 second max for filtered query
        
        # Test reminder task performance
        with patch('risk.notifications.RiskActionReminderService.send_individual_reminder') as mock_send:
            mock_send.return_value = True
            
            start_time = timezone.now()
            result = send_risk_action_due_reminders.apply()
            end_time = timezone.now()
            
            task_time = (end_time - start_time).total_seconds()
            
            self.assertTrue(result.successful())
            self.assertLess(task_time, 5.0)  # 5 seconds max for task