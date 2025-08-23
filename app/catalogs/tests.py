import json
from datetime import date, timedelta
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from django.db import IntegrityError
from rest_framework.test import APITestCase
from rest_framework import status
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from core.models import Tenant
from .models import Framework, Clause, Control, ControlEvidence, FrameworkMapping, ControlAssessment, AssessmentEvidence
from .management.commands.import_framework import Command as ImportCommand
import tempfile
import os

User = get_user_model()


class FrameworkModelTest(TenantTestCase):
    """Test Framework model functionality."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant(name="Test Tenant", schema_name="test")
        cls.tenant.save()
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_framework_creation(self):
        """Test creating a framework with required fields."""
        framework = Framework.objects.create(
            name='Test Framework',
            short_name='TEST',
            version='1.0',
            description='Test framework description',
            framework_type='security',
            issuing_organization='Test Organization',
            effective_date=date.today(),
            created_by=self.user
        )
        
        self.assertEqual(framework.name, 'Test Framework')
        self.assertEqual(framework.short_name, 'TEST')
        self.assertEqual(framework.version, '1.0')
        self.assertTrue(framework.is_active)
        self.assertEqual(str(framework), 'Test Framework v1.0')
    
    def test_framework_unique_constraint(self):
        """Test that name and version combination must be unique."""
        Framework.objects.create(
            name='Test Framework',
            version='1.0',
            issuing_organization='Test Org',
            effective_date=date.today()
        )
        
        with self.assertRaises(IntegrityError):
            Framework.objects.create(
                name='Test Framework',
                version='1.0',
                issuing_organization='Test Org 2',
                effective_date=date.today()
            )
    
    def test_framework_properties(self):
        """Test framework computed properties."""
        framework = Framework.objects.create(
            name='Test Framework',
            version='1.0',
            issuing_organization='Test Org',
            effective_date=date.today(),
            status='active'
        )
        
        self.assertTrue(framework.is_active)
        self.assertEqual(framework.clause_count, 0)
        self.assertEqual(framework.control_count, 0)


class ClauseModelTest(TenantTestCase):
    """Test Clause model functionality."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant(name="Test Tenant", schema_name="test")
        cls.tenant.save()
    
    def setUp(self):
        self.framework = Framework.objects.create(
            name='Test Framework',
            version='1.0',
            issuing_organization='Test Org',
            effective_date=date.today()
        )
    
    def test_clause_creation(self):
        """Test creating a clause with required fields."""
        clause = Clause.objects.create(
            framework=self.framework,
            clause_id='1.1',
            title='Test Clause',
            description='Test clause description',
            sort_order=10
        )
        
        self.assertEqual(clause.clause_id, '1.1')
        self.assertEqual(clause.title, 'Test Clause')
        self.assertEqual(clause.full_clause_id, '1.1')
        self.assertEqual(str(clause), f'{self.framework.short_name} 1.1: Test Clause')
    
    def test_clause_hierarchy(self):
        """Test parent-child clause relationships."""
        parent_clause = Clause.objects.create(
            framework=self.framework,
            clause_id='1',
            title='Parent Clause',
            description='Parent description',
            sort_order=10
        )
        
        child_clause = Clause.objects.create(
            framework=self.framework,
            clause_id='1.1',
            title='Child Clause',
            description='Child description',
            parent_clause=parent_clause,
            sort_order=11
        )
        
        self.assertEqual(child_clause.parent_clause, parent_clause)
        self.assertEqual(child_clause.full_clause_id, '1.1.1')
        self.assertIn(child_clause, parent_clause.subclauses.all())
    
    def test_clause_unique_constraint(self):
        """Test that framework and clause_id combination must be unique."""
        Clause.objects.create(
            framework=self.framework,
            clause_id='1.1',
            title='First Clause',
            description='First description'
        )
        
        with self.assertRaises(IntegrityError):
            Clause.objects.create(
                framework=self.framework,
                clause_id='1.1',
                title='Duplicate Clause',
                description='Duplicate description'
            )
    
    def test_get_all_subclauses(self):
        """Test recursive subclause retrieval."""
        parent = Clause.objects.create(
            framework=self.framework,
            clause_id='1',
            title='Parent',
            description='Parent'
        )
        
        child1 = Clause.objects.create(
            framework=self.framework,
            clause_id='1.1',
            title='Child 1',
            description='Child 1',
            parent_clause=parent
        )
        
        grandchild = Clause.objects.create(
            framework=self.framework,
            clause_id='1.1.1',
            title='Grandchild',
            description='Grandchild',
            parent_clause=child1
        )
        
        all_subclauses = parent.get_all_subclauses()
        self.assertIn(child1, all_subclauses)
        self.assertIn(grandchild, all_subclauses)


class ControlModelTest(TenantTestCase):
    """Test Control model functionality."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant(name="Test Tenant", schema_name="test")
        cls.tenant.save()
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.framework = Framework.objects.create(
            name='Test Framework',
            version='1.0',
            issuing_organization='Test Org',
            effective_date=date.today()
        )
        
        self.clause = Clause.objects.create(
            framework=self.framework,
            clause_id='1.1',
            title='Test Clause',
            description='Test clause description'
        )
    
    def test_control_creation(self):
        """Test creating a control with required fields."""
        control = Control.objects.create(
            control_id='CTRL-001',
            name='Test Control',
            description='Test control description',
            control_type='preventive',
            created_by=self.user
        )
        
        control.clauses.add(self.clause)
        
        self.assertEqual(control.control_id, 'CTRL-001')
        self.assertEqual(control.name, 'Test Control')
        self.assertTrue(control.control_id in str(control))
        self.assertIn(self.clause, control.clauses.all())
    
    def test_control_properties(self):
        """Test control computed properties."""
        control = Control.objects.create(
            control_id='CTRL-001',
            name='Test Control',
            description='Test description',
            control_type='preventive',
            status='active',
            created_by=self.user
        )
        
        control.clauses.add(self.clause)
        
        self.assertTrue(control.is_active)
        self.assertTrue(control.needs_testing)  # No last_tested_date
        self.assertIn(self.framework, control.framework_coverage)
    
    def test_control_needs_testing(self):
        """Test control testing status logic."""
        control = Control.objects.create(
            control_id='CTRL-001',
            name='Test Control',
            description='Test description',
            control_type='preventive',
            created_by=self.user
        )
        
        # No test date - should need testing
        self.assertTrue(control.needs_testing)
        
        # Recent test - should not need testing
        control.last_tested_date = date.today()
        control.save()
        self.assertFalse(control.needs_testing)
        
        # Old test - should need testing
        control.last_tested_date = date.today() - timedelta(days=100)
        control.save()
        self.assertTrue(control.needs_testing)
    
    def test_control_change_log(self):
        """Test control change log functionality."""
        control = Control.objects.create(
            control_id='CTRL-001',
            name='Test Control',
            description='Test description',
            control_type='preventive',
            created_by=self.user
        )
        
        control.add_change_log_entry(self.user, 'Initial creation')
        
        self.assertEqual(len(control.change_log), 1)
        self.assertEqual(control.change_log[0]['user'], self.user.username)
        self.assertEqual(control.change_log[0]['description'], 'Initial creation')
    
    def test_control_unique_constraint(self):
        """Test that control_id must be unique."""
        Control.objects.create(
            control_id='CTRL-001',
            name='First Control',
            description='First description',
            control_type='preventive'
        )
        
        with self.assertRaises(IntegrityError):
            Control.objects.create(
                control_id='CTRL-001',
                name='Duplicate Control',
                description='Duplicate description',
                control_type='detective'
            )


class ControlEvidenceModelTest(TenantTestCase):
    """Test ControlEvidence model functionality."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant(name="Test Tenant", schema_name="test")
        cls.tenant.save()
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.control = Control.objects.create(
            control_id='CTRL-001',
            name='Test Control',
            description='Test description',
            control_type='preventive',
            created_by=self.user
        )
    
    def test_evidence_creation(self):
        """Test creating control evidence."""
        evidence = ControlEvidence.objects.create(
            control=self.control,
            title='Test Evidence',
            evidence_type='document',
            description='Test evidence description',
            evidence_date=date.today(),
            collected_by=self.user
        )
        
        self.assertEqual(evidence.title, 'Test Evidence')
        self.assertEqual(evidence.evidence_type, 'document')
        self.assertFalse(evidence.is_validated)
        self.assertIn('CTRL-001', str(evidence))
    
    def test_evidence_validation(self):
        """Test evidence validation functionality."""
        evidence = ControlEvidence.objects.create(
            control=self.control,
            title='Test Evidence',
            evidence_type='document',
            collected_by=self.user
        )
        
        evidence.validate_evidence(self.user, 'Evidence verified')
        
        self.assertTrue(evidence.is_validated)
        self.assertEqual(evidence.validated_by, self.user)
        self.assertIsNotNone(evidence.validated_at)
        self.assertEqual(evidence.validation_notes, 'Evidence verified')


class FrameworkMappingModelTest(TenantTestCase):
    """Test FrameworkMapping model functionality."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant(name="Test Tenant", schema_name="test")
        cls.tenant.save()
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.framework1 = Framework.objects.create(
            name='Framework 1',
            version='1.0',
            issuing_organization='Org 1',
            effective_date=date.today()
        )
        
        self.framework2 = Framework.objects.create(
            name='Framework 2',
            version='1.0',
            issuing_organization='Org 2',
            effective_date=date.today()
        )
        
        self.clause1 = Clause.objects.create(
            framework=self.framework1,
            clause_id='1.1',
            title='Clause 1',
            description='Description 1'
        )
        
        self.clause2 = Clause.objects.create(
            framework=self.framework2,
            clause_id='A.1',
            title='Clause A',
            description='Description A'
        )
    
    def test_mapping_creation(self):
        """Test creating framework mappings."""
        mapping = FrameworkMapping.objects.create(
            source_clause=self.clause1,
            target_clause=self.clause2,
            mapping_type='equivalent',
            mapping_rationale='Both clauses require the same control',
            confidence_level=90,
            created_by=self.user
        )
        
        self.assertEqual(mapping.source_clause, self.clause1)
        self.assertEqual(mapping.target_clause, self.clause2)
        self.assertEqual(mapping.mapping_type, 'equivalent')
        self.assertEqual(mapping.confidence_level, 90)
    
    def test_mapping_unique_constraint(self):
        """Test that source and target clause combination must be unique."""
        FrameworkMapping.objects.create(
            source_clause=self.clause1,
            target_clause=self.clause2,
            mapping_type='equivalent',
            created_by=self.user
        )
        
        with self.assertRaises(IntegrityError):
            FrameworkMapping.objects.create(
                source_clause=self.clause1,
                target_clause=self.clause2,
                mapping_type='partial',
                created_by=self.user
            )


class ImportFrameworkCommandTest(TransactionTestCase):
    """Test the import_framework management command."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Sample framework data
        self.framework_data = {
            "name": "Test Security Framework",
            "short_name": "TSF",
            "version": "1.0",
            "description": "A test security framework for unit testing",
            "framework_type": "security",
            "issuing_organization": "Test Organization",
            "effective_date": "2024-01-01",
            "status": "active",
            "clauses": [
                {
                    "clause_id": "TSF-1",
                    "title": "Access Control",
                    "description": "Systems must implement proper access controls",
                    "clause_type": "control",
                    "criticality": "high",
                    "sort_order": 10
                },
                {
                    "clause_id": "TSF-2",
                    "title": "Data Protection",
                    "description": "Data must be properly protected",
                    "clause_type": "control",
                    "criticality": "high",
                    "sort_order": 20
                }
            ]
        }
    
    def create_temp_json_file(self, data):
        """Create a temporary JSON file with framework data."""
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.json', 
            delete=False
        )
        json.dump(data, temp_file, indent=2)
        temp_file.close()
        return temp_file.name
    
    def test_import_json_framework(self):
        """Test importing framework from JSON file."""
        temp_file = self.create_temp_json_file(self.framework_data)
        
        try:
            call_command('import_framework', temp_file, user=self.user.username)
            
            # Check framework was created
            framework = Framework.objects.get(name='Test Security Framework')
            self.assertEqual(framework.version, '1.0')
            self.assertEqual(framework.short_name, 'TSF')
            self.assertEqual(framework.issuing_organization, 'Test Organization')
            
            # Check clauses were created
            clauses = framework.clauses.all()
            self.assertEqual(clauses.count(), 2)
            
            tsf1 = clauses.get(clause_id='TSF-1')
            self.assertEqual(tsf1.title, 'Access Control')
            self.assertEqual(tsf1.criticality, 'high')
            
        finally:
            os.unlink(temp_file)
    
    def test_import_with_update_flag(self):
        """Test updating existing framework with --update flag."""
        temp_file = self.create_temp_json_file(self.framework_data)
        
        try:
            # First import
            call_command('import_framework', temp_file, user=self.user.username)
            
            # Modify data
            updated_data = self.framework_data.copy()
            updated_data['description'] = 'Updated description'
            updated_data['clauses'].append({
                "clause_id": "TSF-3",
                "title": "New Clause",
                "description": "A new clause added",
                "clause_type": "control",
                "criticality": "medium",
                "sort_order": 30
            })
            
            updated_file = self.create_temp_json_file(updated_data)
            
            # Second import with update
            call_command('import_framework', updated_file, '--update', user=self.user.username)
            
            framework = Framework.objects.get(name='Test Security Framework')
            self.assertEqual(framework.description, 'Updated description')
            self.assertEqual(framework.clauses.count(), 3)
            
            os.unlink(updated_file)
            
        finally:
            os.unlink(temp_file)


class CatalogsAPITest(APITestCase):
    """Test the catalogs API endpoints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.framework = Framework.objects.create(
            name='API Test Framework',
            version='1.0',
            issuing_organization='Test Org',
            effective_date=date.today(),
            created_by=self.user
        )
        
        self.clause = Clause.objects.create(
            framework=self.framework,
            clause_id='API-1',
            title='API Test Clause',
            description='API test description'
        )
        
        self.control = Control.objects.create(
            control_id='API-CTRL-001',
            name='API Test Control',
            description='API control description',
            control_type='preventive',
            created_by=self.user
        )
        
        self.control.clauses.add(self.clause)
    
    def test_framework_list_endpoint(self):
        """Test the framework list API endpoint."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/catalogs/frameworks/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'API Test Framework')
    
    def test_framework_detail_endpoint(self):
        """Test the framework detail API endpoint."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/catalogs/frameworks/{self.framework.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'API Test Framework')
        self.assertEqual(response.data['clause_count'], 1)
    
    def test_control_list_endpoint(self):
        """Test the control list API endpoint."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/catalogs/controls/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['control_id'], 'API-CTRL-001')
    
    def test_control_testing_endpoint(self):
        """Test the control testing update endpoint."""
        self.client.force_authenticate(user=self.user)
        
        test_data = {
            'test_date': '2024-01-15',
            'test_result': 'fully_effective',
            'notes': 'Control tested successfully'
        }
        
        response = self.client.post(
            f'/api/catalogs/controls/{self.control.id}/update_testing/',
            test_data
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh control from database
        self.control.refresh_from_db()
        self.assertEqual(str(self.control.last_tested_date), '2024-01-15')
        self.assertEqual(self.control.last_test_result, 'fully_effective')
    
    def test_framework_stats_endpoint(self):
        """Test the framework statistics endpoint."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/catalogs/frameworks/{self.framework.id}/stats/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['framework_id'], self.framework.id)
        self.assertEqual(response.data['total_clauses'], 1)
        self.assertEqual(response.data['total_controls'], 1)
    
    def test_unauthorized_access(self):
        """Test that unauthorized users cannot access the API."""
        response = self.client.get('/api/catalogs/frameworks/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ControlAssessmentModelTest(TenantTestCase):
    """Test ControlAssessment model functionality."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant(name="Test Tenant", schema_name="test")
        cls.tenant.save()
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.assigned_user = User.objects.create_user(
            username='assigned_user',
            email='assigned@example.com',
            password='testpass123'
        )
        
        self.framework = Framework.objects.create(
            name='Test Framework',
            version='1.0',
            issuing_organization='Test Org',
            effective_date=date.today()
        )
        
        self.clause = Clause.objects.create(
            framework=self.framework,
            clause_id='1.1',
            title='Test Clause',
            description='Test clause description'
        )
        
        self.control = Control.objects.create(
            control_id='CTRL-001',
            name='Test Control',
            description='Test control description',
            control_type='preventive',
            created_by=self.user
        )
        
        self.control.clauses.add(self.clause)
    
    def test_assessment_creation(self):
        """Test creating a control assessment with required fields."""
        assessment = ControlAssessment.objects.create(
            control=self.control,
            applicability='applicable',
            implementation_status='not_implemented',
            status='pending',
            assigned_to=self.assigned_user,
            due_date=date.today() + timedelta(days=30),
            created_by=self.user
        )
        
        self.assertEqual(assessment.control, self.control)
        self.assertEqual(assessment.applicability, 'applicable')
        self.assertEqual(assessment.implementation_status, 'not_implemented')
        self.assertEqual(assessment.status, 'pending')
        self.assertEqual(assessment.assigned_to, self.assigned_user)
        self.assertIsNotNone(assessment.assessment_id)
        self.assertTrue(assessment.assessment_id.startswith('ASSESS-'))
    
    def test_assessment_str_representation(self):
        """Test string representation of assessment."""
        assessment = ControlAssessment.objects.create(
            control=self.control,
            applicability='applicable',
            created_by=self.user
        )
        
        expected_str = f"{self.control.control_id} - Assessment ({assessment.status})"
        self.assertEqual(str(assessment), expected_str)
    
    def test_assessment_is_overdue_property(self):
        """Test is_overdue property."""
        # Future due date - not overdue
        assessment = ControlAssessment.objects.create(
            control=self.control,
            due_date=date.today() + timedelta(days=10),
            created_by=self.user
        )
        self.assertFalse(assessment.is_overdue)
        
        # Past due date - overdue
        assessment.due_date = date.today() - timedelta(days=1)
        assessment.save()
        self.assertTrue(assessment.is_overdue)
        
        # No due date - not overdue
        assessment.due_date = None
        assessment.save()
        self.assertFalse(assessment.is_overdue)
    
    def test_assessment_days_until_due_property(self):
        """Test days_until_due property."""
        # Future due date
        assessment = ControlAssessment.objects.create(
            control=self.control,
            due_date=date.today() + timedelta(days=5),
            created_by=self.user
        )
        self.assertEqual(assessment.days_until_due, 5)
        
        # Past due date
        assessment.due_date = date.today() - timedelta(days=3)
        assessment.save()
        self.assertEqual(assessment.days_until_due, -3)
        
        # No due date
        assessment.due_date = None
        assessment.save()
        self.assertIsNone(assessment.days_until_due)
    
    def test_assessment_framework_info_property(self):
        """Test framework_info property."""
        assessment = ControlAssessment.objects.create(
            control=self.control,
            created_by=self.user
        )
        
        framework_info = assessment.framework_info
        self.assertEqual(len(framework_info), 1)
        self.assertEqual(framework_info[0]['framework'], self.framework.name)
        self.assertEqual(framework_info[0]['version'], self.framework.version)
    
    def test_assessment_add_change_log_entry(self):
        """Test adding change log entries."""
        assessment = ControlAssessment.objects.create(
            control=self.control,
            created_by=self.user
        )
        
        assessment.add_change_log_entry(self.user, 'Initial assessment created')
        
        self.assertEqual(len(assessment.change_log), 1)
        self.assertEqual(assessment.change_log[0]['user'], self.user.username)
        self.assertEqual(assessment.change_log[0]['description'], 'Initial assessment created')
        self.assertIn('timestamp', assessment.change_log[0])
    
    def test_assessment_update_status(self):
        """Test updating assessment status."""
        assessment = ControlAssessment.objects.create(
            control=self.control,
            status='pending',
            created_by=self.user
        )
        
        assessment.update_status('in_progress', self.user, 'Started working on assessment')
        
        self.assertEqual(assessment.status, 'in_progress')
        self.assertEqual(len(assessment.change_log), 1)
        self.assertIn('Status changed to in_progress', assessment.change_log[0]['description'])
    
    def test_assessment_unique_constraint(self):
        """Test that control assessment is unique per control."""
        ControlAssessment.objects.create(
            control=self.control,
            created_by=self.user
        )
        
        with self.assertRaises(IntegrityError):
            ControlAssessment.objects.create(
                control=self.control,
                created_by=self.assigned_user
            )
    
    def test_assessment_status_transitions(self):
        """Test valid status transitions."""
        assessment = ControlAssessment.objects.create(
            control=self.control,
            status='not_started',
            created_by=self.user
        )
        
        # Valid transitions
        valid_transitions = [
            ('not_started', 'pending'),
            ('pending', 'in_progress'),
            ('in_progress', 'under_review'),
            ('under_review', 'complete'),
        ]
        
        for from_status, to_status in valid_transitions:
            assessment.status = from_status
            assessment.save()
            assessment.update_status(to_status, self.user)
            self.assertEqual(assessment.status, to_status)


class AssessmentEvidenceModelTest(TenantTestCase):
    """Test AssessmentEvidence model functionality."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tenant = Tenant(name="Test Tenant", schema_name="test")
        cls.tenant.save()
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.framework = Framework.objects.create(
            name='Test Framework',
            version='1.0',
            issuing_organization='Test Org',
            effective_date=date.today()
        )
        
        self.clause = Clause.objects.create(
            framework=self.framework,
            clause_id='1.1',
            title='Test Clause',
            description='Test clause description'
        )
        
        self.control = Control.objects.create(
            control_id='CTRL-001',
            name='Test Control',
            description='Test control description',
            control_type='preventive',
            created_by=self.user
        )
        
        self.control.clauses.add(self.clause)
        
        self.assessment = ControlAssessment.objects.create(
            control=self.control,
            applicability='applicable',
            created_by=self.user
        )
        
        self.evidence = ControlEvidence.objects.create(
            control=self.control,
            title='Test Evidence',
            evidence_type='document',
            description='Test evidence description',
            evidence_date=date.today(),
            collected_by=self.user
        )
    
    def test_assessment_evidence_creation(self):
        """Test creating assessment evidence link."""
        assessment_evidence = AssessmentEvidence.objects.create(
            assessment=self.assessment,
            evidence=self.evidence,
            relevance_score=85,
            notes='This evidence supports the assessment',
            linked_by=self.user
        )
        
        self.assertEqual(assessment_evidence.assessment, self.assessment)
        self.assertEqual(assessment_evidence.evidence, self.evidence)
        self.assertEqual(assessment_evidence.relevance_score, 85)
        self.assertEqual(assessment_evidence.notes, 'This evidence supports the assessment')
        self.assertEqual(assessment_evidence.linked_by, self.user)
    
    def test_assessment_evidence_str_representation(self):
        """Test string representation of assessment evidence."""
        assessment_evidence = AssessmentEvidence.objects.create(
            assessment=self.assessment,
            evidence=self.evidence,
            linked_by=self.user
        )
        
        expected_str = f"{self.assessment.assessment_id} - {self.evidence.title}"
        self.assertEqual(str(assessment_evidence), expected_str)
    
    def test_assessment_evidence_unique_constraint(self):
        """Test that assessment and evidence combination must be unique."""
        AssessmentEvidence.objects.create(
            assessment=self.assessment,
            evidence=self.evidence,
            linked_by=self.user
        )
        
        with self.assertRaises(IntegrityError):
            AssessmentEvidence.objects.create(
                assessment=self.assessment,
                evidence=self.evidence,
                linked_by=self.user
            )
    
    def test_assessment_evidence_relevance_score_validation(self):
        """Test relevance score constraints."""
        # Valid score
        assessment_evidence = AssessmentEvidence.objects.create(
            assessment=self.assessment,
            evidence=self.evidence,
            relevance_score=75,
            linked_by=self.user
        )
        self.assertEqual(assessment_evidence.relevance_score, 75)


class ControlAssessmentAPITest(APITestCase):
    """Test the control assessment API endpoints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.assigned_user = User.objects.create_user(
            username='assigned_user',
            email='assigned@example.com',
            password='testpass123'
        )
        
        self.framework = Framework.objects.create(
            name='API Test Framework',
            version='1.0',
            issuing_organization='Test Org',
            effective_date=date.today(),
            created_by=self.user
        )
        
        self.clause = Clause.objects.create(
            framework=self.framework,
            clause_id='API-1',
            title='API Test Clause',
            description='API test description'
        )
        
        self.control = Control.objects.create(
            control_id='API-CTRL-001',
            name='API Test Control',
            description='API control description',
            control_type='preventive',
            created_by=self.user
        )
        
        self.control.clauses.add(self.clause)
        
        self.assessment = ControlAssessment.objects.create(
            control=self.control,
            applicability='applicable',
            implementation_status='partially_implemented',
            status='pending',
            assigned_to=self.assigned_user,
            due_date=date.today() + timedelta(days=30),
            created_by=self.user
        )
    
    def test_assessment_list_endpoint(self):
        """Test the assessment list API endpoint."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/catalogs/assessments/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['control']['control_id'], 'API-CTRL-001')
    
    def test_assessment_detail_endpoint(self):
        """Test the assessment detail API endpoint."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/catalogs/assessments/{self.assessment.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['applicability'], 'applicable')
        self.assertEqual(response.data['implementation_status'], 'partially_implemented')
        self.assertEqual(response.data['status'], 'pending')
    
    def test_assessment_create_endpoint(self):
        """Test creating assessment via API."""
        control2 = Control.objects.create(
            control_id='API-CTRL-002',
            name='Second API Control',
            description='Second control description',
            control_type='detective',
            created_by=self.user
        )
        control2.clauses.add(self.clause)
        
        self.client.force_authenticate(user=self.user)
        
        assessment_data = {
            'control': control2.id,
            'applicability': 'applicable',
            'implementation_status': 'implemented',
            'status': 'in_progress',
            'assigned_to': self.assigned_user.id,
            'due_date': (date.today() + timedelta(days=60)).isoformat(),
            'assessment_notes': 'New assessment via API'
        }
        
        response = self.client.post('/api/catalogs/assessments/', assessment_data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['applicability'], 'applicable')
        self.assertEqual(response.data['implementation_status'], 'implemented')
    
    def test_assessment_update_endpoint(self):
        """Test updating assessment via API."""
        self.client.force_authenticate(user=self.user)
        
        update_data = {
            'status': 'in_progress',
            'implementation_status': 'implemented',
            'assessment_notes': 'Updated assessment status'
        }
        
        response = self.client.patch(f'/api/catalogs/assessments/{self.assessment.id}/', update_data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'in_progress')
        self.assertEqual(response.data['implementation_status'], 'implemented')
    
    def test_assessment_status_update_endpoint(self):
        """Test the assessment status update endpoint."""
        self.client.force_authenticate(user=self.user)
        
        status_data = {
            'status': 'complete',
            'notes': 'Assessment completed successfully'
        }
        
        response = self.client.post(
            f'/api/catalogs/assessments/{self.assessment.id}/update_status/',
            status_data
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'complete')
        
        # Verify change log was updated
        self.assessment.refresh_from_db()
        self.assertEqual(len(self.assessment.change_log), 1)
        self.assertIn('Status changed to complete', self.assessment.change_log[0]['description'])
    
    def test_bulk_assessment_creation_endpoint(self):
        """Test bulk assessment creation endpoint."""
        # Create additional controls
        for i in range(3):
            control = Control.objects.create(
                control_id=f'BULK-CTRL-{i:03d}',
                name=f'Bulk Control {i}',
                description=f'Bulk control {i} description',
                control_type='preventive',
                created_by=self.user
            )
            control.clauses.add(self.clause)
        
        self.client.force_authenticate(user=self.user)
        
        bulk_data = {
            'framework_id': self.framework.id,
            'default_due_date': (date.today() + timedelta(days=90)).isoformat(),
            'default_assigned_to': self.assigned_user.id
        }
        
        response = self.client.post('/api/catalogs/assessments/bulk_create/', bulk_data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['created_count'], 3)  # Excluding existing assessment
        self.assertEqual(len(response.data['assessments']), 3)
    
    def test_assessment_progress_endpoint(self):
        """Test assessment progress reporting endpoint."""
        # Create additional assessments with different statuses
        for i, status_val in enumerate(['in_progress', 'complete', 'not_applicable']):
            control = Control.objects.create(
                control_id=f'PROG-CTRL-{i:03d}',
                name=f'Progress Control {i}',
                description=f'Progress control {i} description',
                control_type='preventive',
                created_by=self.user
            )
            control.clauses.add(self.clause)
            
            ControlAssessment.objects.create(
                control=control,
                status=status_val,
                applicability='applicable' if status_val != 'not_applicable' else 'not_applicable',
                created_by=self.user
            )
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/catalogs/assessments/progress/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_assessments'], 4)
        self.assertIn('status_breakdown', response.data)
        self.assertIn('applicability_breakdown', response.data)
        self.assertIn('implementation_breakdown', response.data)
    
    def test_assessment_filtering(self):
        """Test assessment filtering options."""
        self.client.force_authenticate(user=self.user)
        
        # Filter by status
        response = self.client.get('/api/catalogs/assessments/?status=pending')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Filter by applicability
        response = self.client.get('/api/catalogs/assessments/?applicability=applicable')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        # Filter by assigned user
        response = self.client.get(f'/api/catalogs/assessments/?assigned_to={self.assigned_user.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_assessment_evidence_endpoints(self):
        """Test assessment evidence API endpoints."""
        evidence = ControlEvidence.objects.create(
            control=self.control,
            title='API Test Evidence',
            evidence_type='document',
            description='API evidence description',
            evidence_date=date.today(),
            collected_by=self.user
        )
        
        self.client.force_authenticate(user=self.user)
        
        # Create assessment evidence link
        evidence_data = {
            'assessment': self.assessment.id,
            'evidence': evidence.id,
            'relevance_score': 90,
            'notes': 'Highly relevant evidence'
        }
        
        response = self.client.post('/api/catalogs/assessment-evidence/', evidence_data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['relevance_score'], 90)
        self.assertEqual(response.data['notes'], 'Highly relevant evidence')
        
        # List assessment evidence
        response = self.client.get('/api/catalogs/assessment-evidence/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_unauthorized_assessment_access(self):
        """Test that unauthorized users cannot access assessments."""
        response = self.client.get('/api/catalogs/assessments/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class EvidenceManagementAPITest(APITestCase):
    """Test the evidence management API endpoints for assessments."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.framework = Framework.objects.create(
            name='Evidence Test Framework',
            version='1.0',
            issuing_organization='Test Org',
            effective_date=date.today(),
            created_by=self.user
        )
        
        self.clause = Clause.objects.create(
            framework=self.framework,
            clause_id='EV-1',
            title='Evidence Test Clause',
            description='Evidence test description'
        )
        
        self.control = Control.objects.create(
            control_id='EV-CTRL-001',
            name='Evidence Test Control',
            description='Evidence control description',
            control_type='preventive',
            created_by=self.user
        )
        
        self.control.clauses.add(self.clause)
        
        self.assessment = ControlAssessment.objects.create(
            control=self.control,
            applicability='applicable',
            status='pending',
            created_by=self.user
        )
    
    def test_direct_evidence_upload(self):
        """Test uploading evidence directly to an assessment."""
        self.client.force_authenticate(user=self.user)
        
        # Create a test file
        from io import BytesIO
        from django.core.files.uploadedfile import InMemoryUploadedFile
        
        file_content = b"Test evidence document content"
        test_file = InMemoryUploadedFile(
            BytesIO(file_content),
            None,
            'test_evidence.txt',
            'text/plain',
            len(file_content),
            None
        )
        
        data = {
            'file': test_file,
            'title': 'Test Evidence Document',
            'description': 'Test document description',
            'evidence_title': 'Assessment Evidence',
            'evidence_type': 'document',
            'evidence_description': 'Evidence for testing',
            'evidence_purpose': 'Primary testing evidence',
            'is_primary_evidence': True
        }
        
        response = self.client.post(
            f'/api/catalogs/assessments/{self.assessment.id}/upload_evidence/',
            data,
            format='multipart'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
        self.assertIn('document', response.data)
        self.assertIn('evidence', response.data)
        self.assertIn('assessment_link', response.data)
        
        # Verify evidence was created and linked
        self.assertEqual(AssessmentEvidence.objects.count(), 1)
        evidence_link = AssessmentEvidence.objects.first()
        self.assertEqual(evidence_link.assessment, self.assessment)
        self.assertTrue(evidence_link.is_primary_evidence)
    
    def test_assessment_evidence_listing(self):
        """Test getting all evidence for an assessment."""
        self.client.force_authenticate(user=self.user)
        
        # Create some evidence manually
        from core.models import Document
        
        document = Document.objects.create(
            title='Test Evidence Doc',
            uploaded_by=self.user
        )
        
        evidence = ControlEvidence.objects.create(
            control=self.control,
            title='Test Evidence',
            evidence_type='document',
            document=document,
            collected_by=self.user
        )
        
        AssessmentEvidence.objects.create(
            assessment=self.assessment,
            evidence=evidence,
            evidence_purpose='Testing purpose',
            is_primary_evidence=True,
            created_by=self.user
        )
        
        response = self.client.get(
            f'/api/catalogs/assessments/{self.assessment.id}/evidence/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['evidence_count'], 1)
        self.assertEqual(len(response.data['evidence']), 1)
        self.assertEqual(response.data['evidence'][0]['evidence_purpose'], 'Testing purpose')
        self.assertTrue(response.data['evidence'][0]['is_primary_evidence'])
    
    def test_assessment_list_includes_evidence_info(self):
        """Test that assessment list includes evidence count and primary evidence flag."""
        self.client.force_authenticate(user=self.user)
        
        # Create evidence linked to assessment
        from core.models import Document
        
        document = Document.objects.create(
            title='Test Evidence Doc',
            uploaded_by=self.user
        )
        
        evidence = ControlEvidence.objects.create(
            control=self.control,
            title='Test Evidence',
            evidence_type='document',
            document=document,
            collected_by=self.user
        )
        
        AssessmentEvidence.objects.create(
            assessment=self.assessment,
            evidence=evidence,
            is_primary_evidence=True,
            created_by=self.user
        )
        
        response = self.client.get('/api/catalogs/assessments/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        
        assessment_data = response.data['results'][0]
        self.assertIn('evidence_count', assessment_data)
        self.assertIn('has_primary_evidence', assessment_data)
        self.assertEqual(assessment_data['evidence_count'], 1)
        self.assertTrue(assessment_data['has_primary_evidence'])