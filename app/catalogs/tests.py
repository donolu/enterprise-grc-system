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
from .models import Framework, Clause, Control, ControlEvidence, FrameworkMapping
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