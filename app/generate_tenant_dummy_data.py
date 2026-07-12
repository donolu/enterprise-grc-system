#!/usr/bin/env python3
# ruff: noqa: E402, S105, S311
"""Comprehensive tenant dummy data generator for the GRC platform.

Generates realistic dummy data within tenant context across all GRC modules:
- 10+ Risk records with categories and treatment strategies
- 8+ Framework and compliance records
- 6+ Control assessments
- User accounts and audit trails

Total: 42+ comprehensive records spread across all functionalities
"""

import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal
import random
import uuid

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings.local')
django.setup()

from django.db import connection
from django_tenants.utils import tenant_context
from core.models import Tenant
from django.contrib.auth import get_user_model
from django.utils import timezone

DEMO_PASSWORD_ENV = 'GRC_DEMO_USER_PASSWORD'


def apply_demo_password(user):
    """Use an opt-in demo password, otherwise disable password login."""
    password = os.environ.get(DEMO_PASSWORD_ENV)
    if password:
        user.set_password(password)
    else:
        user.set_unusable_password()
    user.save()


class TenantDummyDataGenerator:
    def __init__(self, tenant_schema='demo'):
        self.tenant = Tenant.objects.get(schema_name=tenant_schema)

    def run(self):
        """Generate all dummy data within tenant context"""
        with tenant_context(self.tenant):
            print(f'🚀 Starting GRC Dummy Data Generation for {self.tenant.name}...')
            print('=' * 60)
            print(f'✅ Running within schema: {connection.schema_name}')

            # Import models within tenant context
            from risk.models import RiskCategory, Risk
            from catalogs.models import Framework, Clause, Control, ControlAssessment
            from core.models import AuditEvent

            User = get_user_model()

            try:
                # Create users first
                users = self.create_users()

                # Create risk data
                risk_categories, risks = self.create_risk_data(users)

                # Create compliance framework data
                frameworks, clauses, controls = self.create_compliance_data(users)

                # Create assessments
                assessments = self.create_assessment_data(users, controls)

                # Create audit events
                audit_events = self.create_audit_data(users)

                print('\n' + '=' * 60)
                print('🎉 DUMMY DATA GENERATION COMPLETE!')
                print('=' * 60)
                print(f'✅ Users: {len(users)}')
                print(f'✅ Risk Categories: {len(risk_categories)}')
                print(f'✅ Risks: {len(risks)}')
                print(f'✅ Frameworks: {len(frameworks)}')
                print(f'✅ Clauses: {len(clauses)}')
                print(f'✅ Controls: {len(controls)}')
                print(f'✅ Assessments: {len(assessments)}')
                print(f'✅ Audit Events: {len(audit_events)}')
                print(f'📊 Total Records: {len(users) + len(risk_categories) + len(risks) + len(frameworks) + len(clauses) + len(controls) + len(assessments) + len(audit_events)}')
                print('=' * 60)

                return True

            except Exception as e:
                print(f'❌ Error during data generation: {e}')
                import traceback
                traceback.print_exc()
                return False

    def create_users(self):
        """Create test users"""
        print('\n🧑‍💼 Creating users...')
        User = get_user_model()

        users_data = [
            {'username': 'admin', 'first_name': 'System', 'last_name': 'Administrator', 'email': 'admin@demo.com', 'is_staff': True, 'is_superuser': True},
            {'username': 'risk_manager', 'first_name': 'Sarah', 'last_name': 'Johnson', 'email': 'sarah.johnson@demo.com', 'is_staff': True},
            {'username': 'security_analyst', 'first_name': 'David', 'last_name': 'Wilson', 'email': 'david.wilson@demo.com'},
            {'username': 'compliance_officer', 'first_name': 'Maria', 'last_name': 'Rodriguez', 'email': 'maria.rodriguez@demo.com'},
            {'username': 'auditor', 'first_name': 'James', 'last_name': 'Brown', 'email': 'james.brown@demo.com'},
            {'username': 'policy_manager', 'first_name': 'Emma', 'last_name': 'Davis', 'email': 'emma.davis@demo.com'},
            {'username': 'vendor_manager', 'first_name': 'Michael', 'last_name': 'Chen', 'email': 'michael.chen@demo.com'},
        ]

        created_users = []
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults=user_data
            )
            if created:
                apply_demo_password(user)
            created_users.append(user)
            print(f'   ✅ {user.get_full_name()} ({user.username})')

        print(f'✅ Created {len(created_users)} users')
        if not os.environ.get(DEMO_PASSWORD_ENV):
            print(f'ℹ️  Users have unusable passwords. Set {DEMO_PASSWORD_ENV} to enable demo login.')
        return created_users

    def create_risk_data(self, users):
        """Create risk categories and risks"""
        print('\n🚨 Creating risk data...')
        from risk.models import RiskCategory, Risk

        # Create risk categories
        categories_data = [
            {'name': 'Cybersecurity', 'description': 'Information security and cyber threats', 'color': '#dc2626'},
            {'name': 'Operational', 'description': 'Business operations and processes', 'color': '#ea580c'},
            {'name': 'Compliance', 'description': 'Regulatory compliance risks', 'color': '#7c3aed'},
            {'name': 'Financial', 'description': 'Financial and credit risks', 'color': '#059669'},
            {'name': 'Strategic', 'description': 'Strategic planning and execution risks', 'color': '#0284c7'},
            {'name': 'Reputational', 'description': 'Brand and reputation risks', 'color': '#9333ea'}
        ]

        created_categories = []
        for cat_data in categories_data:
            category, created = RiskCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            created_categories.append(category)

        # Create risks
        risks_data = [
            {
                'title': 'Cloud Data Exposure Risk',
                'description': 'Potential unauthorised access to sensitive data stored in cloud infrastructure',
                'category': created_categories[0],  # Cybersecurity
                'impact': 4, 'likelihood': 3, 'risk_level': 'high',
                'status': 'identified', 'treatment_strategy': 'mitigate'
            },
            {
                'title': 'Third-party Vendor Security Risk',
                'description': 'Risk of data exposure through third-party vendors with inadequate security controls',
                'category': created_categories[1],  # Operational
                'impact': 3, 'likelihood': 3, 'risk_level': 'medium',
                'status': 'assessed', 'treatment_strategy': 'mitigate'
            },
            {
                'title': 'Regulatory Compliance Violation',
                'description': 'Risk of penalties due to failure to comply with GDPR and other regulations',
                'category': created_categories[2],  # Compliance
                'impact': 5, 'likelihood': 2, 'risk_level': 'medium',
                'status': 'treatment_planned', 'treatment_strategy': 'mitigate'
            },
            {
                'title': 'Supply Chain Disruption',
                'description': 'Risk of operational disruption due to supplier failure or logistics issues',
                'category': created_categories[1],  # Operational
                'impact': 4, 'likelihood': 2, 'risk_level': 'medium',
                'status': 'identified', 'treatment_strategy': 'mitigate'
            },
            {
                'title': 'Insider Threat Risk',
                'description': 'Risk of malicious or accidental data breach by internal employees',
                'category': created_categories[0],  # Cybersecurity
                'impact': 5, 'likelihood': 1, 'risk_level': 'medium',
                'status': 'assessed', 'treatment_strategy': 'accept'
            },
            {
                'title': 'Financial Fraud Risk',
                'description': 'Risk of fraudulent financial transactions and accounting irregularities',
                'category': created_categories[3],  # Financial
                'impact': 5, 'likelihood': 2, 'risk_level': 'high',
                'status': 'treatment_in_progress', 'treatment_strategy': 'mitigate'
            },
            {
                'title': 'Technology Infrastructure Failure',
                'description': 'Risk of critical system failures affecting business operations',
                'category': created_categories[1],  # Operational
                'impact': 4, 'likelihood': 3, 'risk_level': 'high',
                'status': 'mitigated', 'treatment_strategy': 'mitigate'
            },
            {
                'title': 'Data Privacy Breach',
                'description': 'Risk of unauthorised disclosure of personal customer data',
                'category': created_categories[0],  # Cybersecurity
                'impact': 5, 'likelihood': 2, 'risk_level': 'high',
                'status': 'identified', 'treatment_strategy': 'mitigate'
            },
            {
                'title': 'Market Volatility Risk',
                'description': 'Risk of financial losses due to adverse market conditions',
                'category': created_categories[4],  # Strategic
                'impact': 3, 'likelihood': 4, 'risk_level': 'medium',
                'status': 'accepted', 'treatment_strategy': 'accept'
            },
            {
                'title': 'Reputation Damage Risk',
                'description': 'Risk of brand damage due to negative publicity or incidents',
                'category': created_categories[5],  # Reputational
                'impact': 4, 'likelihood': 2, 'risk_level': 'medium',
                'status': 'identified', 'treatment_strategy': 'transfer'
            },
            {
                'title': 'Regulatory Change Risk',
                'description': 'Risk of non-compliance due to evolving regulatory requirements',
                'category': created_categories[2],  # Compliance
                'impact': 3, 'likelihood': 4, 'risk_level': 'medium',
                'status': 'treatment_planned', 'treatment_strategy': 'mitigate'
            },
            {
                'title': 'Business Continuity Risk',
                'description': 'Risk of extended business disruption due to disaster or crisis',
                'category': created_categories[1],  # Operational
                'impact': 5, 'likelihood': 1, 'risk_level': 'medium',
                'status': 'mitigated', 'treatment_strategy': 'mitigate'
            }
        ]

        created_risks = []
        for i, risk_data in enumerate(risks_data, 1):
            risk_data.update({
                'risk_id': f'RISK-2024-{i:03d}',
                'risk_owner': random.choice(users),
                'identified_date': timezone.now().date() - timedelta(days=random.randint(30, 180)),
                'next_review_date': timezone.now().date() + timedelta(days=random.randint(30, 90)),
                'created_by': random.choice(users[:3])  # Admins
            })

            risk, created = Risk.objects.get_or_create(
                risk_id=risk_data['risk_id'],
                defaults=risk_data
            )
            created_risks.append(risk)
            print(f'   ✅ {risk.risk_id}: {risk.title}')

        print(f'✅ Created {len(created_categories)} risk categories and {len(created_risks)} risks')
        return created_categories, created_risks

    def create_compliance_data(self, users):
        """Create frameworks, clauses, and controls"""
        print('\n📋 Creating compliance framework data...')
        from catalogs.models import Framework, Clause, Control

        # Create frameworks
        frameworks_data = [
            {
                'name': 'SOC 2 Type II',
                'short_name': 'SOC2',
                'description': 'System and Organization Controls 2 Type II audit framework',
                'framework_type': 'security',
                'issuing_organization': 'AICPA',
                'version': '2017',
                'effective_date': timezone.now().date() - timedelta(days=365),
                'status': 'active',
                'is_mandatory': True
            },
            {
                'name': 'ISO 27001:2013',
                'short_name': 'ISO27001',
                'description': 'Information Security Management System standard',
                'framework_type': 'security',
                'issuing_organization': 'ISO/IEC',
                'version': '2013',
                'effective_date': timezone.now().date() - timedelta(days=730),
                'status': 'active',
                'is_mandatory': True
            },
            {
                'name': 'NIST Cybersecurity Framework',
                'short_name': 'NIST-CSF',
                'description': 'NIST Framework for Improving Critical Infrastructure Cybersecurity',
                'framework_type': 'security',
                'issuing_organization': 'NIST',
                'version': '1.1',
                'effective_date': timezone.now().date() - timedelta(days=1095),
                'status': 'active',
                'is_mandatory': False
            },
            {
                'name': 'GDPR Compliance Framework',
                'short_name': 'GDPR',
                'description': 'General Data Protection Regulation compliance framework',
                'framework_type': 'privacy',
                'issuing_organization': 'European Commission',
                'version': '2016',
                'effective_date': timezone.now().date() - timedelta(days=2190),
                'status': 'active',
                'is_mandatory': True
            },
            {
                'name': 'PCI DSS',
                'short_name': 'PCI',
                'description': 'Payment Card Industry Data Security Standard',
                'framework_type': 'financial',
                'issuing_organization': 'PCI Security Standards Council',
                'version': '4.0',
                'effective_date': timezone.now().date() - timedelta(days=180),
                'status': 'active',
                'is_mandatory': True
            }
        ]

        created_frameworks = []
        for fw_data in frameworks_data:
            fw_data['created_by'] = random.choice(users[:3])
            framework, created = Framework.objects.get_or_create(
                short_name=fw_data['short_name'],
                defaults=fw_data
            )
            created_frameworks.append(framework)
            print(f'   ✅ {framework.short_name}: {framework.name}')

        # Create clauses for each framework
        created_clauses = []
        for framework in created_frameworks[:2]:  # Just create clauses for first 2 frameworks
            if framework.short_name == 'SOC2':
                clauses_data = [
                    {
                        'clause_id': 'CC6.1',
                        'title': 'Logical and Physical Access Controls',
                        'description': 'The entity implements logical and physical access controls to protect against threats from sources outside its system boundaries.',
                        'clause_type': 'control',
                        'criticality': 'high',
                        'is_testable': True
                    },
                    {
                        'clause_id': 'CC6.2',
                        'title': 'Access Control Management',
                        'description': 'Prior to issuing system credentials and granting system access, the entity registers and authorizes new internal and external users whose access is administered by the entity.',
                        'clause_type': 'control',
                        'criticality': 'high',
                        'is_testable': True
                    },
                    {
                        'clause_id': 'CC7.1',
                        'title': 'System Monitoring',
                        'description': 'To meet its objectives, the entity uses detection and monitoring procedures to identify security events.',
                        'clause_type': 'monitoring',
                        'criticality': 'medium',
                        'is_testable': True
                    }
                ]
            else:  # ISO27001
                clauses_data = [
                    {
                        'clause_id': 'A.8.2.1',
                        'title': 'Classification of Information',
                        'description': 'Information should be classified in terms of legal requirements, value, criticality and sensitivity.',
                        'clause_type': 'policy',
                        'criticality': 'high',
                        'is_testable': True
                    },
                    {
                        'clause_id': 'A.9.1.1',
                        'title': 'Access Control Policy',
                        'description': 'An access control policy should be established, documented and reviewed.',
                        'clause_type': 'policy',
                        'criticality': 'critical',
                        'is_testable': True
                    }
                ]

            for i, clause_data in enumerate(clauses_data):
                clause_data.update({
                    'framework': framework,
                    'sort_order': i + 1
                })
                clause, created = Clause.objects.get_or_create(
                    framework=framework,
                    clause_id=clause_data['clause_id'],
                    defaults=clause_data
                )
                created_clauses.append(clause)
                print(f'     ✅ {clause.clause_id}: {clause.title}')

        # Create controls
        controls_data = [
            {
                'name': 'Multi-Factor Authentication',
                'description': 'Implement multi-factor authentication for all user accounts with access to sensitive systems',
                'control_id': 'CTRL-001',
                'control_type': 'preventive',
                'automation_level': 'automated',
                'status': 'active',
                'frequency': 'Continuous'
            },
            {
                'name': 'Data Encryption at Rest',
                'description': 'Encrypt all sensitive data stored in databases and file systems',
                'control_id': 'CTRL-002',
                'control_type': 'preventive',
                'automation_level': 'automated',
                'status': 'active',
                'frequency': 'Continuous'
            },
            {
                'name': 'Regular Security Training',
                'description': 'Conduct mandatory security awareness training for all employees',
                'control_id': 'CTRL-003',
                'control_type': 'preventive',
                'automation_level': 'manual',
                'status': 'active',
                'frequency': 'Annually'
            },
            {
                'name': 'Vulnerability Scanning',
                'description': 'Perform regular vulnerability scans of all systems and applications',
                'control_id': 'CTRL-004',
                'control_type': 'detective',
                'automation_level': 'semi_automated',
                'status': 'active',
                'frequency': 'Monthly'
            },
            {
                'name': 'Incident Response Plan',
                'description': 'Maintain and test incident response procedures',
                'control_id': 'CTRL-005',
                'control_type': 'corrective',
                'automation_level': 'manual',
                'status': 'active',
                'frequency': 'Quarterly'
            },
            {
                'name': 'Access Review Process',
                'description': 'Regular review and certification of user access rights',
                'control_id': 'CTRL-006',
                'control_type': 'detective',
                'automation_level': 'semi_automated',
                'status': 'active',
                'frequency': 'Quarterly'
            },
            {
                'name': 'Data Backup and Recovery',
                'description': 'Regular backup of critical data with tested recovery procedures',
                'control_id': 'CTRL-007',
                'control_type': 'corrective',
                'automation_level': 'automated',
                'status': 'active',
                'frequency': 'Daily'
            },
            {
                'name': 'Network Segmentation',
                'description': 'Implement network segmentation to isolate sensitive systems',
                'control_id': 'CTRL-008',
                'control_type': 'preventive',
                'automation_level': 'automated',
                'status': 'active',
                'frequency': 'Continuous'
            }
        ]

        created_controls = []
        for control_data in controls_data:
            control_data.update({
                'control_owner': random.choice(users),
                'created_by': random.choice(users[:3]),
                'last_tested_date': timezone.now().date() - timedelta(days=random.randint(15, 60))
            })
            control, created = Control.objects.get_or_create(
                control_id=control_data['control_id'],
                defaults=control_data
            )

            # Link controls to clauses
            if created_clauses:
                control.clauses.add(random.choice(created_clauses))

            created_controls.append(control)
            print(f'   ✅ {control.control_id}: {control.name}')

        print(f'✅ Created {len(created_frameworks)} frameworks, {len(created_clauses)} clauses, and {len(created_controls)} controls')
        return created_frameworks, created_clauses, created_controls

    def create_assessment_data(self, users, controls):
        """Create control assessments"""
        print('\n🔍 Creating control assessments...')
        from catalogs.models import ControlAssessment

        if not controls:
            print('⚠️  No controls available for assessments')
            return []

        created_assessments = []
        for i, control in enumerate(controls[:6]):  # Create assessments for first 6 controls
            assessment_data = {
                'control': control,
                'assessment_id': f'ASS-{control.control_id}-{uuid.uuid4().hex[:8].upper()}',
                'applicability': 'applicable',
                'status': random.choice(['in_progress', 'complete', 'under_review', 'pending']),
                'implementation_status': random.choice(['implemented', 'partially_implemented', 'not_implemented']),
                'assigned_to': random.choice(users),
                'reviewer': random.choice(users[:3]),
                'due_date': timezone.now().date() + timedelta(days=random.randint(30, 90)),
                'current_state_description': f'Current implementation status of {control.name}',
                'gap_analysis': f'Analysis of gaps for {control.name}',
                'maturity_level': random.choice(['repeatable', 'defined', 'managed']),
                'risk_rating': random.choice(['low', 'medium', 'high']),
                'compliance_score': random.randint(70, 95),
                'created_by': random.choice(users[:3])
            }

            assessment = ControlAssessment.objects.create(**assessment_data)
            created_assessments.append(assessment)
            print(f'   ✅ {assessment.assessment_id}: {assessment.control.name}')

        print(f'✅ Created {len(created_assessments)} control assessments')
        return created_assessments

    def create_audit_data(self, users):
        """Create audit events"""
        print('\n📊 Creating audit events...')
        from core.models import AuditEvent

        events_data = [
            {'event': 'risk_created', 'details': {'risk_id': 'RISK-2024-001', 'title': 'Cloud Data Exposure Risk'}},
            {'event': 'risk_updated', 'details': {'risk_id': 'RISK-2024-002', 'field': 'status', 'old_value': 'identified', 'new_value': 'assessed'}},
            {'event': 'user_login', 'details': {'username': 'risk_manager', 'ip_address': '192.168.1.100'}},
            {'event': 'framework_imported', 'details': {'framework': 'SOC 2 Type II', 'clauses_count': 3}},
            {'event': 'assessment_completed', 'details': {'assessment_id': 'ASS-CTRL-001', 'score': 85}},
            {'event': 'control_tested', 'details': {'control_id': 'CTRL-001', 'result': 'effective'}},
            {'event': 'report_generated', 'details': {'report_type': 'risk_summary', 'format': 'pdf'}},
            {'event': 'user_created', 'details': {'username': 'security_analyst', 'role': 'analyst'}},
            {'event': 'policy_updated', 'details': {'policy': 'Information Security Policy', 'version': '2.1'}},
            {'event': 'export_data', 'details': {'data_type': 'risks', 'format': 'csv', 'records': 12}}
        ]

        created_events = []
        for event_data in events_data:
            event_data.update({
                'user': random.choice(users),
                'at': timezone.now() - timedelta(hours=random.randint(1, 168))  # Last week
            })
            event = AuditEvent.objects.create(**event_data)
            created_events.append(event)
            print(f'   ✅ {event.event}: {event.user.username}')

        print(f'✅ Created {len(created_events)} audit events')
        return created_events


if __name__ == '__main__':
    generator = TenantDummyDataGenerator()
    success = generator.run()

    if success:
        print('\n🎯 Ready to test Django APIs!')
        print('   1. Risk endpoints: /api/risk/risks/')
        print('   2. Categories: /api/risk/categories/')
        print('   3. Analytics: /analytics/executive/')
        print('   4. All data created in tenant schema: demo')
        exit(0)
    else:
        print('\n❌ Dummy data generation failed')
        exit(1)
