#!/usr/bin/env python3
# ruff: noqa: E402, S105, S311
"""Comprehensive dummy data generator for the GRC platform.

Generates realistic dummy data across all GRC modules:
- 10 Risk records with categories and treatment strategies
- 8 Vendor records with contacts and services
- 8 Policy records with versions and acknowledgements
- 6 Training videos with categories
- 5 Framework and compliance records
- 5 Analytics/audit records

Total: 42 comprehensive records spread across all functionalities
"""

from pathlib import Path
import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal
import random
import uuid

# Setup Django environment
APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings.test')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from risk.models import Risk, RiskCategory, RiskMatrix
from vendors.models import Vendor, VendorCategory, VendorContact, VendorService, VendorTask
from policies.models import Policy, PolicyCategory, PolicyVersion, PolicyAcknowledgment
from training.models import TrainingVideo, TrainingCategory, SecurityAwarenessCampaign
from catalogs.models import Framework, Clause, Control, ControlAssessment

User = get_user_model()
DEMO_PASSWORD_ENV = 'GRC_DEMO_USER_PASSWORD'


def apply_demo_password(user):
    """Use an opt-in demo password, otherwise disable password login."""
    password = os.environ.get(DEMO_PASSWORD_ENV)
    if password:
        user.set_password(password)
    else:
        user.set_unusable_password()
    user.save()


class GRCDataGenerator:
    def __init__(self):
        self.users = []
        self.risk_categories = []
        self.vendor_categories = []
        self.policy_categories = []
        self.training_categories = []
        self.frameworks = []

    def create_users(self):
        """Create test users for the GRC system"""
        users_data = [
            {'username': 'admin', 'email': 'admin@company.com', 'first_name': 'System', 'last_name': 'Admin', 'is_staff': True},
            {'username': 'risk_manager', 'email': 'risk.manager@company.com', 'first_name': 'Sarah', 'last_name': 'Johnson'},
            {'username': 'compliance_officer', 'email': 'compliance@company.com', 'first_name': 'Michael', 'last_name': 'Chen'},
            {'username': 'security_analyst', 'email': 'security@company.com', 'first_name': 'David', 'last_name': 'Wilson'},
            {'username': 'vendor_manager', 'email': 'vendor.mgmt@company.com', 'first_name': 'Jennifer', 'last_name': 'Garcia'},
            {'username': 'policy_owner', 'email': 'policy@company.com', 'first_name': 'Robert', 'last_name': 'Brown'},
            {'username': 'training_coord', 'email': 'training@company.com', 'first_name': 'Lisa', 'last_name': 'Martinez'},
        ]

        for user_data in users_data:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'is_staff': user_data.get('is_staff', False),
                    'is_active': True
                }
            )
            if created:
                apply_demo_password(user)
            self.users.append(user)

        print(f"✅ Created {len(self.users)} users")
        if not os.environ.get(DEMO_PASSWORD_ENV):
            print(f"ℹ️  Users have unusable passwords. Set {DEMO_PASSWORD_ENV} to enable demo login.")

    def create_risk_data(self):
        """Generate 10 comprehensive risk records"""
        # Create Risk Categories
        risk_cats_data = [
            {'name': 'Cybersecurity', 'description': 'Information security and cyber threats', 'color': '#dc2626'},
            {'name': 'Operational', 'description': 'Business operations and processes', 'color': '#ea580c'},
            {'name': 'Financial', 'description': 'Financial and credit risks', 'color': '#16a34a'},
            {'name': 'Regulatory', 'description': 'Compliance and regulatory risks', 'color': '#7c2d12'},
            {'name': 'Strategic', 'description': 'Strategic and reputational risks', 'color': '#7c3aed'},
        ]

        for cat_data in risk_cats_data:
            category, _ = RiskCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            self.risk_categories.append(category)

        # Create Risk Matrix
        matrix, _ = RiskMatrix.objects.get_or_create(
            name="Standard 5x5 Matrix",
            defaults={
                'description': 'Standard 5x5 risk assessment matrix',
                'impact_levels': [
                    {'level': 1, 'name': 'Very Low', 'description': 'Minimal impact'},
                    {'level': 2, 'name': 'Low', 'description': 'Minor impact'},
                    {'level': 3, 'name': 'Medium', 'description': 'Moderate impact'},
                    {'level': 4, 'name': 'High', 'description': 'Major impact'},
                    {'level': 5, 'name': 'Very High', 'description': 'Severe impact'}
                ],
                'likelihood_levels': [
                    {'level': 1, 'name': 'Very Unlikely', 'description': '<10% chance'},
                    {'level': 2, 'name': 'Unlikely', 'description': '10-30% chance'},
                    {'level': 3, 'name': 'Possible', 'description': '30-60% chance'},
                    {'level': 4, 'name': 'Likely', 'description': '60-90% chance'},
                    {'level': 5, 'name': 'Very Likely', 'description': '>90% chance'}
                ],
                'risk_levels': {
                    'low': {'min_score': 1, 'max_score': 6, 'color': '#16a34a'},
                    'medium': {'min_score': 7, 'max_score': 12, 'color': '#ea580c'},
                    'high': {'min_score': 13, 'max_score': 20, 'color': '#dc2626'},
                    'critical': {'min_score': 21, 'max_score': 25, 'color': '#7c2d12'}
                }
            }
        )

        # Generate 10 Risk records
        risks_data = [
            {
                'title': 'Cloud Data Breach Risk',
                'description': 'Potential unauthorised access to sensitive data stored in cloud infrastructure due to misconfiguration or compromised credentials.',
                'category': 0, 'impact': 5, 'likelihood': 3, 'status': 'mitigating',
                'treatment_strategy': 'mitigate', 'owner': 3
            },
            {
                'title': 'Third-party Vendor Security Risk',
                'description': 'Risk of data exposure through third-party vendors with inadequate security controls or compromised systems.',
                'category': 0, 'impact': 4, 'likelihood': 3, 'status': 'assessed',
                'treatment_strategy': 'mitigate', 'owner': 4
            },
            {
                'title': 'Ransomware Attack Risk',
                'description': 'Risk of business disruption and data loss due to ransomware attacks targeting critical business systems.',
                'category': 0, 'impact': 5, 'likelihood': 2, 'status': 'identified',
                'treatment_strategy': 'mitigate', 'owner': 3
            },
            {
                'title': 'Regulatory Non-compliance Risk',
                'description': 'Risk of penalties and sanctions due to failure to comply with GDPR, SOX, or other regulatory requirements.',
                'category': 3, 'impact': 4, 'likelihood': 2, 'status': 'under_review',
                'treatment_strategy': 'mitigate', 'owner': 2
            },
            {
                'title': 'Supply Chain Disruption Risk',
                'description': 'Risk of operational disruption due to critical supplier failure or supply chain interruption.',
                'category': 1, 'impact': 3, 'likelihood': 3, 'status': 'mitigating',
                'treatment_strategy': 'mitigate', 'owner': 4
            },
            {
                'title': 'Key Personnel Departure Risk',
                'description': 'Risk of knowledge loss and operational disruption due to unexpected departure of key technical personnel.',
                'category': 1, 'impact': 3, 'likelihood': 2, 'status': 'identified',
                'treatment_strategy': 'accept', 'owner': 1
            },
            {
                'title': 'Market Volatility Risk',
                'description': 'Risk of revenue impact due to economic downturn and market volatility affecting customer demand.',
                'category': 2, 'impact': 4, 'likelihood': 3, 'status': 'monitored',
                'treatment_strategy': 'accept', 'owner': 1
            },
            {
                'title': 'Technology Obsolescence Risk',
                'description': 'Risk of competitive disadvantage due to outdated technology stack and legacy system dependencies.',
                'category': 4, 'impact': 3, 'likelihood': 4, 'status': 'identified',
                'treatment_strategy': 'mitigate', 'owner': 3
            },
            {
                'title': 'Data Privacy Violation Risk',
                'description': 'Risk of privacy violations and regulatory penalties due to inadequate personal data protection measures.',
                'category': 3, 'impact': 4, 'likelihood': 2, 'status': 'assessed',
                'treatment_strategy': 'mitigate', 'owner': 2
            },
            {
                'title': 'Physical Security Breach Risk',
                'description': 'Risk of unauthorised physical access to facilities and sensitive areas compromising data and systems.',
                'category': 0, 'impact': 2, 'likelihood': 2, 'status': 'mitigated',
                'treatment_strategy': 'mitigate', 'owner': 3
            }
        ]

        for i, risk_data in enumerate(risks_data):
            risk_score = risk_data['impact'] * risk_data['likelihood']
            if risk_score <= 6:
                risk_level = 'low'
            elif risk_score <= 12:
                risk_level = 'medium'
            elif risk_score <= 20:
                risk_level = 'high'
            else:
                risk_level = 'critical'

            risk = Risk.objects.create(
                title=risk_data['title'],
                description=risk_data['description'],
                category=self.risk_categories[risk_data['category']],
                risk_matrix=matrix,
                impact=risk_data['impact'],
                likelihood=risk_data['likelihood'],
                risk_score=risk_score,
                risk_level=risk_level,
                status=risk_data['status'],
                treatment_strategy=risk_data['treatment_strategy'],
                risk_owner=self.users[risk_data['owner']],
                identified_by=self.users[1],
                identified_date=timezone.now().date() - timedelta(days=random.randint(30, 180)),
                next_review_date=timezone.now().date() + timedelta(days=random.randint(30, 90)),
                created_by=self.users[1]
            )

        print("✅ Created 10 risk records with categories and matrix")

    def create_vendor_data(self):
        """Generate 8 comprehensive vendor records"""
        # Create Vendor Categories
        vendor_cats_data = [
            {'name': 'Cloud Services', 'description': 'Cloud infrastructure and SaaS providers', 'color_code': '#3b82f6', 'risk_weight': 'high'},
            {'name': 'Professional Services', 'description': 'Consulting and professional service providers', 'color_code': '#10b981', 'risk_weight': 'medium'},
            {'name': 'Technology Vendors', 'description': 'Software and hardware technology providers', 'color_code': '#f59e0b', 'risk_weight': 'medium'},
            {'name': 'Financial Services', 'description': 'Banking, payment, and financial service providers', 'color_code': '#ef4444', 'risk_weight': 'high'},
        ]

        for cat_data in vendor_cats_data:
            category, _ = VendorCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            self.vendor_categories.append(category)

        # Generate 8 Vendor records
        vendors_data = [
            {
                'name': 'Microsoft Corporation',
                'category': 0, 'status': 'active', 'vendor_type': 'service_provider',
                'risk_level': 'low', 'annual_spend': 120000.00,
                'contact': {'first_name': 'John', 'last_name': 'Smith', 'email': 'john.smith@microsoft.com', 'title': 'Account Manager'}
            },
            {
                'name': 'Amazon Web Services',
                'category': 0, 'status': 'active', 'vendor_type': 'service_provider',
                'risk_level': 'medium', 'annual_spend': 240000.00,
                'contact': {'first_name': 'Sarah', 'last_name': 'Johnson', 'email': 'sarah.j@aws.amazon.com', 'title': 'Solutions Architect'}
            },
            {
                'name': 'Deloitte Consulting',
                'category': 1, 'status': 'active', 'vendor_type': 'consultant',
                'risk_level': 'medium', 'annual_spend': 85000.00,
                'contact': {'first_name': 'Michael', 'last_name': 'Chen', 'email': 'mchen@deloitte.com', 'title': 'Senior Consultant'}
            },
            {
                'name': 'Okta Inc.',
                'category': 2, 'status': 'active', 'vendor_type': 'service_provider',
                'risk_level': 'medium', 'annual_spend': 45000.00,
                'contact': {'first_name': 'Jennifer', 'last_name': 'Wilson', 'email': 'jwilson@okta.com', 'title': 'Customer Success Manager'}
            },
            {
                'name': 'CrowdStrike Holdings',
                'category': 2, 'status': 'active', 'vendor_type': 'service_provider',
                'risk_level': 'low', 'annual_spend': 72000.00,
                'contact': {'first_name': 'David', 'last_name': 'Brown', 'email': 'dbrown@crowdstrike.com', 'title': 'Security Specialist'}
            },
            {
                'name': 'JPMorgan Chase Bank',
                'category': 3, 'status': 'active', 'vendor_type': 'service_provider',
                'risk_level': 'low', 'annual_spend': 24000.00,
                'contact': {'first_name': 'Lisa', 'last_name': 'Garcia', 'email': 'lgarcia@jpmorgan.com', 'title': 'Relationship Manager'}
            },
            {
                'name': 'Atlassian Corporation',
                'category': 2, 'status': 'under_review', 'vendor_type': 'service_provider',
                'risk_level': 'medium', 'annual_spend': 36000.00,
                'contact': {'first_name': 'Robert', 'last_name': 'Martinez', 'email': 'rmartinez@atlassian.com', 'title': 'Account Executive'}
            },
            {
                'name': 'KPMG LLP',
                'category': 1, 'status': 'approved', 'vendor_type': 'consultant',
                'risk_level': 'low', 'annual_spend': 95000.00,
                'contact': {'first_name': 'Amanda', 'last_name': 'Taylor', 'email': 'ataylor@kpmg.com', 'title': 'Partner'}
            }
        ]

        for vendor_data in vendors_data:
            vendor = Vendor.objects.create(
                name=vendor_data['name'],
                category=self.vendor_categories[vendor_data['category']],
                status=vendor_data['status'],
                vendor_type=vendor_data['vendor_type'],
                risk_level=vendor_data['risk_level'],
                annual_spend=Decimal(str(vendor_data['annual_spend'])),
                assigned_to=self.users[4],  # vendor_manager
                relationship_start_date=timezone.now().date() - timedelta(days=random.randint(365, 1095)),
                contract_start_date=timezone.now().date() - timedelta(days=random.randint(180, 365)),
                contract_end_date=timezone.now().date() + timedelta(days=random.randint(180, 730)),
                created_by=self.users[4]
            )

            # Create contact for each vendor
            contact_data = vendor_data['contact']
            VendorContact.objects.create(
                vendor=vendor,
                first_name=contact_data['first_name'],
                last_name=contact_data['last_name'],
                email=contact_data['email'],
                title=contact_data['title'],
                contact_type='primary',
                is_primary=True
            )

        print("✅ Created 8 vendor records with contacts and categories")

    def create_policy_data(self):
        """Generate 8 comprehensive policy records"""
        # Create Policy Categories
        policy_cats_data = [
            {'name': 'Information Security', 'description': 'Information security policies and procedures', 'color': '#dc2626'},
            {'name': 'Human Resources', 'description': 'HR policies and employee guidelines', 'color': '#16a34a'},
            {'name': 'Compliance', 'description': 'Regulatory compliance policies', 'color': '#7c3aed'},
            {'name': 'Operations', 'description': 'Business operations and procedures', 'color': '#ea580c'},
        ]

        for cat_data in policy_cats_data:
            category, _ = PolicyCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            self.policy_categories.append(category)

        # Generate 8 Policy records
        policies_data = [
            {
                'title': 'Information Security Policy',
                'category': 0, 'policy_type': 'policy', 'status': 'approved',
                'version': '2.1', 'summary': 'Updated encryption requirements and incident response procedures'
            },
            {
                'title': 'Data Classification Standard',
                'category': 0, 'policy_type': 'standard', 'status': 'approved',
                'version': '1.3', 'summary': 'Added new data retention requirements and cloud storage guidelines'
            },
            {
                'title': 'Remote Work Policy',
                'category': 1, 'policy_type': 'policy', 'status': 'approved',
                'version': '1.5', 'summary': 'Updated VPN requirements and home office security standards'
            },
            {
                'title': 'Incident Response Procedure',
                'category': 0, 'policy_type': 'procedure', 'status': 'approved',
                'version': '3.0', 'summary': 'Major update to incident classification and escalation procedures'
            },
            {
                'title': 'Vendor Risk Assessment Framework',
                'category': 2, 'policy_type': 'framework', 'status': 'approved',
                'version': '1.2', 'summary': 'Enhanced third-party risk evaluation criteria'
            },
            {
                'title': 'Employee Onboarding Checklist',
                'category': 1, 'policy_type': 'procedure', 'status': 'under_review',
                'version': '2.0', 'summary': 'Streamlined onboarding process with digital forms'
            },
            {
                'title': 'Business Continuity Plan',
                'category': 3, 'policy_type': 'procedure', 'status': 'approved',
                'version': '1.8', 'summary': 'Updated recovery time objectives and disaster scenarios'
            },
            {
                'title': 'Code of Conduct',
                'category': 1, 'policy_type': 'policy', 'status': 'approved',
                'version': '4.0', 'summary': 'Annual review with updated ethics guidelines and reporting procedures'
            }
        ]

        for policy_data in policies_data:
            policy = Policy.objects.create(
                title=policy_data['title'],
                category=self.policy_categories[policy_data['category']],
                policy_type=policy_data['policy_type'],
                status=policy_data['status'],
                owner=self.users[5],  # policy_owner
                approver=self.users[2] if policy_data['status'] == 'approved' else None,
                review_frequency_months=12,
                requires_acknowledgment=True,
                created_by=self.users[5]
            )

            # Create policy version
            version = PolicyVersion.objects.create(
                policy=policy,
                version_number=policy_data['version'],
                summary=policy_data['summary'],
                is_active=True,
                is_published=policy_data['status'] == 'approved',
                effective_date=timezone.now().date() - timedelta(days=random.randint(30, 180)),
                approved_at=timezone.now() if policy_data['status'] == 'approved' else None,
                approved_by=self.users[2] if policy_data['status'] == 'approved' else None,
                created_by=self.users[5]
            )

        print("✅ Created 8 policy records with versions and categories")

    def create_training_data(self):
        """Generate 6 comprehensive training records"""
        # Create Training Categories
        training_cats_data = [
            {'name': 'Security Awareness', 'description': 'General security awareness training', 'color': '#dc2626'},
            {'name': 'Phishing Prevention', 'description': 'How to identify and avoid phishing attacks', 'color': '#ea580c'},
            {'name': 'Data Protection', 'description': 'Data handling and privacy best practices', 'color': '#16a34a'},
        ]

        for cat_data in training_cats_data:
            category, _ = TrainingCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults=cat_data
            )
            self.training_categories.append(category)

        # Generate 6 Training videos
        videos_data = [
            {
                'title': 'Introduction to Cybersecurity',
                'description': 'Learn the fundamentals of cybersecurity and why it matters for every employee.',
                'category': 0, 'difficulty': 'beginner', 'duration': 15,
                'video_url': 'https://synthesia.io/embed/abc123'
            },
            {
                'title': 'Spotting Phishing Emails',
                'description': 'Learn to identify common phishing techniques and protect yourself from email-based attacks.',
                'category': 1, 'difficulty': 'intermediate', 'duration': 22,
                'video_url': 'https://synthesia.io/embed/def456'
            },
            {
                'title': 'Password Security Best Practices',
                'description': 'Create strong passwords and use multi-factor authentication to secure your accounts.',
                'category': 0, 'difficulty': 'beginner', 'duration': 18,
                'video_url': 'https://synthesia.io/embed/ghi789'
            },
            {
                'title': 'Data Classification Guidelines',
                'description': 'Understand how to properly classify and handle sensitive organisational data.',
                'category': 2, 'difficulty': 'intermediate', 'duration': 28,
                'video_url': 'https://synthesia.io/embed/jkl012'
            },
            {
                'title': 'Social Engineering Attacks',
                'description': 'Recognize and defend against social engineering tactics used by cybercriminals.',
                'category': 1, 'difficulty': 'advanced', 'duration': 25,
                'video_url': 'https://synthesia.io/embed/mno345'
            },
            {
                'title': 'Secure Remote Work Practices',
                'description': 'Best practices for maintaining security while working from home or remote locations.',
                'category': 0, 'difficulty': 'intermediate', 'duration': 20,
                'video_url': 'https://synthesia.io/embed/pqr678'
            }
        ]

        for video_data in videos_data:
            video = TrainingVideo.objects.create(
                title=video_data['title'],
                description=video_data['description'],
                category=self.training_categories[video_data['category']],
                video_provider='synthesia',
                video_url=video_data['video_url'],
                duration_minutes=video_data['duration'],
                difficulty_level=video_data['difficulty'],
                is_published=True,
                published_at=timezone.now() - timedelta(days=random.randint(30, 180)),
                created_by=self.users[6],  # training_coord
                view_count=random.randint(50, 500)
            )

        print("✅ Created 6 training videos with categories")

    def create_framework_data(self):
        """Generate 5 compliance framework records"""
        # Generate 5 Framework records
        frameworks_data = [
            {
                'name': 'ISO 27001:2022 Information Security Management',
                'short_name': 'ISO27001', 'type': 'security',
                'organization': 'International Organization for Standardization',
                'version': '2022', 'status': 'active', 'mandatory': True,
                'clauses': [
                    {'id': 'A.5.1', 'title': 'Information Security Policies', 'type': 'policy'},
                    {'id': 'A.8.2', 'title': 'Data Classification', 'type': 'control'},
                    {'id': 'A.12.6', 'title': 'Management of Technical Vulnerabilities', 'type': 'control'}
                ]
            },
            {
                'name': 'SOC 2 Type II Service Organization Control',
                'short_name': 'SOC2', 'type': 'operational',
                'organization': 'American Institute of CPAs',
                'version': '2017', 'status': 'active', 'mandatory': True,
                'clauses': [
                    {'id': 'CC6.1', 'title': 'Logical and Physical Access Controls', 'type': 'control'},
                    {'id': 'CC7.1', 'title': 'System Operations', 'type': 'control'}
                ]
            },
            {
                'name': 'NIST Cybersecurity Framework',
                'short_name': 'NIST-CSF', 'type': 'security',
                'organization': 'National Institute of Standards and Technology',
                'version': '1.1', 'status': 'active', 'mandatory': False,
                'clauses': [
                    {'id': 'ID.AM-1', 'title': 'Physical devices and systems inventory', 'type': 'control'},
                    {'id': 'PR.AC-1', 'title': 'Access control policy and procedures', 'type': 'policy'}
                ]
            },
            {
                'name': 'PCI Data Security Standard',
                'short_name': 'PCI-DSS', 'type': 'financial',
                'organization': 'PCI Security Standards Council',
                'version': '4.0', 'status': 'active', 'mandatory': True,
                'clauses': [
                    {'id': '1.1.1', 'title': 'Firewall configuration standards', 'type': 'control'},
                    {'id': '2.1', 'title': 'Change default passwords', 'type': 'control'}
                ]
            },
            {
                'name': 'GDPR General Data Protection Regulation',
                'short_name': 'GDPR', 'type': 'privacy',
                'organization': 'European Union',
                'version': '2018', 'status': 'active', 'mandatory': True,
                'clauses': [
                    {'id': 'Art.32', 'title': 'Security of processing', 'type': 'control'},
                    {'id': 'Art.33', 'title': 'Data breach notification', 'type': 'procedure'}
                ]
            }
        ]

        for fw_data in frameworks_data:
            framework = Framework.objects.create(
                name=fw_data['name'],
                short_name=fw_data['short_name'],
                description=f"Compliance framework for {fw_data['name']}",
                framework_type=fw_data['type'],
                issuing_organization=fw_data['organization'],
                version=fw_data['version'],
                effective_date=timezone.now().date() - timedelta(days=random.randint(365, 1095)),
                status=fw_data['status'],
                is_mandatory=fw_data['mandatory'],
                created_by=self.users[2]  # compliance_officer
            )
            self.frameworks.append(framework)

            # Create clauses for each framework
            for clause_data in fw_data['clauses']:
                Clause.objects.create(
                    framework=framework,
                    clause_id=clause_data['id'],
                    title=clause_data['title'],
                    description=f"Detailed requirements for {clause_data['title']}",
                    clause_type=clause_data['type'],
                    criticality='high' if framework.is_mandatory else 'medium',
                    is_testable=True
                )

        print("✅ Created 5 compliance frameworks with clauses")

    def create_analytics_data(self):
        """Generate 5 analytics and audit records"""
        # Create some control assessments for analytics
        controls_data = [
            {'name': 'Access Control Management', 'type': 'technical', 'status': 'active'},
            {'name': 'Data Encryption Standards', 'type': 'technical', 'status': 'active'},
            {'name': 'Incident Response Plan', 'type': 'administrative', 'status': 'active'},
            {'name': 'Vendor Security Assessment', 'type': 'administrative', 'status': 'testing'},
            {'name': 'Employee Security Training', 'type': 'administrative', 'status': 'implemented'}
        ]

        for i, control_data in enumerate(controls_data):
            control = Control.objects.create(
                name=control_data['name'],
                description=f"Control for {control_data['name']}",
                control_id=f"CTRL-{i+1:03d}",
                control_type=control_data['type'],
                status=control_data['status'],
                control_owner=self.users[3],  # security_analyst
                created_by=self.users[2]  # compliance_officer
            )

            # Link control to framework clauses
            if self.frameworks:
                framework = random.choice(self.frameworks)
                clauses = framework.clauses.all()
                if clauses:
                    control.clauses.add(random.choice(clauses))

            # Create control assessment
            assessment = ControlAssessment.objects.create(
                control=control,
                applicability='applicable',
                status=random.choice(['in_progress', 'complete', 'under_review']),
                implementation_status=random.choice(['implemented', 'partially_implemented']),
                assigned_to=self.users[3],
                reviewer=self.users[2],
                due_date=timezone.now().date() + timedelta(days=random.randint(30, 90)),
                current_state_description=f"Current implementation status for {control.name}",
                target_state_description=f"Target state for {control.name}",
                maturity_level=random.choice(['defined', 'managed', 'optimized']),
                compliance_score=random.randint(75, 95),
                created_by=self.users[2]
            )

        print("✅ Created 5 control assessments for analytics")

    def run(self):
        """Execute the complete dummy data generation process"""
        print("🚀 Starting GRC Dummy Data Generation...")
        print("=" * 60)

        try:
            self.create_users()
            self.create_risk_data()
            self.create_vendor_data()
            self.create_policy_data()
            self.create_training_data()
            self.create_framework_data()
            self.create_analytics_data()

            print("=" * 60)
            print("🎉 Successfully generated comprehensive GRC dummy data!")
            print(f"📊 Summary:")
            print(f"   - 7 users (admin, managers, analysts)")
            print(f"   - 10 risk records with categories and treatment plans")
            print(f"   - 8 vendor records with contacts and services")
            print(f"   - 8 policy records with versions and categories")
            print(f"   - 6 training videos with categories")
            print(f"   - 5 compliance frameworks with clauses")
            print(f"   - 5 control assessments for analytics")
            print(f"   🎯 Total: 42+ comprehensive GRC records")
            print("=" * 60)

        except Exception as e:
            print(f"❌ Error during data generation: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    generator = GRCDataGenerator()
    generator.run()
