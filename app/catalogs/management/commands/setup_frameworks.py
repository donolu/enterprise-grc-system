from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from catalogs.models import Framework, Clause


class Command(BaseCommand):
    help = 'Set up basic compliance frameworks for initial deployment'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--framework',
            choices=['soc2', 'iso27001', 'nist', 'all'],
            default='all',
            help='Which framework(s) to set up'
        )
    
    def handle(self, *args, **options):
        framework_choice = options['framework']
        
        if framework_choice in ['soc2', 'all']:
            self.setup_soc2_framework()
        
        if framework_choice in ['iso27001', 'all']:
            self.setup_iso27001_framework()
        
        if framework_choice in ['nist', 'all']:
            self.setup_nist_framework()
        
        self.stdout.write(self.style.SUCCESS('Framework setup completed'))
    
    def setup_soc2_framework(self):
        """Set up SOC 2 Type II framework with key trust service criteria."""
        
        with transaction.atomic():
            framework, created = Framework.objects.get_or_create(
                name='SOC 2 Type II',
                version='2017',
                defaults={
                    'short_name': 'SOC2',
                    'description': 'Service Organization Control 2 Type II - Trust Services Criteria for Security, Availability, Processing Integrity, Confidentiality, and Privacy',
                    'framework_type': 'security',
                    'external_id': 'SOC2-2017',
                    'issuing_organization': 'American Institute of Certified Public Accountants (AICPA)',
                    'official_url': 'https://www.aicpa.org/interestareas/frc/assuranceadvisoryservices/aicpasoc2report.html',
                    'effective_date': timezone.now().date(),
                    'status': 'active',
                    'is_mandatory': False,
                }
            )
            
            if created:
                self.stdout.write('Created SOC 2 framework')
                
                # Security criteria
                security_clauses = [
                    {
                        'clause_id': 'CC6.1',
                        'title': 'Logical and Physical Access Controls',
                        'description': 'The entity implements logical and physical access controls to protect against threats from sources outside its system boundaries.',
                        'sort_order': 10
                    },
                    {
                        'clause_id': 'CC6.2',
                        'title': 'Access Control Management',
                        'description': 'Prior to issuing system credentials and granting system access, the entity registers and authorizes new internal and external users whose access is administered by the entity.',
                        'sort_order': 20
                    },
                    {
                        'clause_id': 'CC6.3',
                        'title': 'Network Access Controls',
                        'description': 'The entity authorizes, modifies, or removes access to data, software, functions, and other protected information assets based on roles, responsibilities, or the system design and changes.',
                        'sort_order': 30
                    },
                    {
                        'clause_id': 'CC7.1',
                        'title': 'Detection of Unauthorized Access',
                        'description': 'To meet its objectives, the entity uses detection and monitoring procedures to identify (1) changes to configurations that result in the introduction of new vulnerabilities, and (2) susceptibilities to newly discovered vulnerabilities.',
                        'sort_order': 40
                    },
                    {
                        'clause_id': 'CC7.2',
                        'title': 'Monitoring of Controls',
                        'description': 'The entity monitors system components and the operation of controls at a frequency sufficient to prevent or detect processing deviations and security violations.',
                        'sort_order': 50
                    },
                ]
                
                # Availability criteria
                availability_clauses = [
                    {
                        'clause_id': 'A1.1',
                        'title': 'Availability Performance Monitoring',
                        'description': 'The entity maintains, monitors, and evaluates current processing capacity and use of system components (infrastructure, data, and software) to manage capacity demand and to enable the implementation of additional capacity to help meet its objectives.',
                        'sort_order': 60
                    },
                    {
                        'clause_id': 'A1.2',
                        'title': 'System Recovery and Backup',
                        'description': 'The entity authorizes, designs, develops or acquires, implements, operates, approves, maintains, and monitors environmental protections, software, data backup processes, and recovery infrastructure to meet its objectives.',
                        'sort_order': 70
                    },
                ]
                
                all_clauses = security_clauses + availability_clauses
                
                for clause_data in all_clauses:
                    Clause.objects.create(
                        framework=framework,
                        clause_id=clause_data['clause_id'],
                        title=clause_data['title'],
                        description=clause_data['description'],
                        sort_order=clause_data['sort_order'],
                        clause_type='control',
                        criticality='high' if 'CC6' in clause_data['clause_id'] else 'medium',
                    )
                
                self.stdout.write(f'Created {len(all_clauses)} SOC 2 clauses')
            else:
                self.stdout.write('SOC 2 framework already exists')
    
    def setup_iso27001_framework(self):
        """Set up ISO 27001:2022 framework with key controls."""
        
        with transaction.atomic():
            framework, created = Framework.objects.get_or_create(
                name='ISO/IEC 27001:2022',
                version='2022',
                defaults={
                    'short_name': 'ISO27001',
                    'description': 'Information Security Management Systems - Requirements',
                    'framework_type': 'security',
                    'external_id': 'ISO27001-2022',
                    'issuing_organization': 'International Organization for Standardization (ISO)',
                    'official_url': 'https://www.iso.org/standard/27001',
                    'effective_date': timezone.now().date(),
                    'status': 'active',
                    'is_mandatory': False,
                }
            )
            
            if created:
                self.stdout.write('Created ISO 27001 framework')
                
                # Key Annex A controls
                iso_clauses = [
                    {
                        'clause_id': 'A.8.1.1',
                        'title': 'Inventory of information assets',
                        'description': 'Information assets associated with information and information processing facilities should be identified and an inventory of these assets should be drawn up and maintained.',
                        'sort_order': 10
                    },
                    {
                        'clause_id': 'A.8.1.2',
                        'title': 'Ownership of assets',
                        'description': 'Assets maintained in the inventory should be owned.',
                        'sort_order': 20
                    },
                    {
                        'clause_id': 'A.9.1.1',
                        'title': 'Access control policy',
                        'description': 'An access control policy should be established, documented and reviewed based on business and information security requirements.',
                        'sort_order': 30
                    },
                    {
                        'clause_id': 'A.9.1.2',
                        'title': 'Access to networks and network services',
                        'description': 'Users should only be provided with access to the network and network services that they have been specifically authorized to use.',
                        'sort_order': 40
                    },
                    {
                        'clause_id': 'A.12.6.1',
                        'title': 'Management of technical vulnerabilities',
                        'description': 'Information about technical vulnerabilities of information systems being used should be obtained in a timely fashion, the organization\'s exposure to such vulnerabilities evaluated and appropriate measures taken to address the associated risk.',
                        'sort_order': 50
                    },
                ]
                
                for clause_data in iso_clauses:
                    Clause.objects.create(
                        framework=framework,
                        clause_id=clause_data['clause_id'],
                        title=clause_data['title'],
                        description=clause_data['description'],
                        sort_order=clause_data['sort_order'],
                        clause_type='control',
                        criticality='high',
                    )
                
                self.stdout.write(f'Created {len(iso_clauses)} ISO 27001 clauses')
            else:
                self.stdout.write('ISO 27001 framework already exists')
    
    def setup_nist_framework(self):
        """Set up NIST Cybersecurity Framework with key functions."""
        
        with transaction.atomic():
            framework, created = Framework.objects.get_or_create(
                name='NIST Cybersecurity Framework',
                version='1.1',
                defaults={
                    'short_name': 'NIST-CSF',
                    'description': 'Framework for Improving Critical Infrastructure Cybersecurity',
                    'framework_type': 'security',
                    'external_id': 'NIST-CSF-1.1',
                    'issuing_organization': 'National Institute of Standards and Technology (NIST)',
                    'official_url': 'https://www.nist.gov/cyberframework',
                    'effective_date': timezone.now().date(),
                    'status': 'active',
                    'is_mandatory': False,
                }
            )
            
            if created:
                self.stdout.write('Created NIST Cybersecurity Framework')
                
                # Core functions and categories
                nist_clauses = [
                    {
                        'clause_id': 'ID.AM-1',
                        'title': 'Physical devices and systems inventory',
                        'description': 'Physical devices and systems within the organization are inventoried',
                        'sort_order': 10
                    },
                    {
                        'clause_id': 'ID.AM-2',
                        'title': 'Software platforms and applications inventory',
                        'description': 'Software platforms and applications within the organization are inventoried',
                        'sort_order': 20
                    },
                    {
                        'clause_id': 'PR.AC-1',
                        'title': 'Identity management and authentication',
                        'description': 'Identities and credentials are issued, managed, verified, revoked, and audited for authorized devices, users and processes',
                        'sort_order': 30
                    },
                    {
                        'clause_id': 'PR.AC-4',
                        'title': 'Access permissions and authorizations',
                        'description': 'Access permissions and authorizations are managed, incorporating the principles of least privilege and separation of duties',
                        'sort_order': 40
                    },
                    {
                        'clause_id': 'DE.CM-1',
                        'title': 'Network monitoring',
                        'description': 'The network is monitored to detect potential cybersecurity events',
                        'sort_order': 50
                    },
                ]
                
                for clause_data in nist_clauses:
                    Clause.objects.create(
                        framework=framework,
                        clause_id=clause_data['clause_id'],
                        title=clause_data['title'],
                        description=clause_data['description'],
                        sort_order=clause_data['sort_order'],
                        clause_type='control',
                        criticality='medium',
                    )
                
                self.stdout.write(f'Created {len(nist_clauses)} NIST CSF clauses')
            else:
                self.stdout.write('NIST Cybersecurity Framework already exists')