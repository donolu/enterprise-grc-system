import json
import yaml
import hashlib
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_date
from django.db import transaction
from catalogs.models import Framework, Clause
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Import compliance frameworks from structured JSON or YAML files'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Path to framework definition file (JSON or YAML)'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing framework if it already exists'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Username of user importing the framework',
            default='system'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing'
        )
    
    def handle(self, *args, **options):
        file_path = Path(options['file_path'])
        
        if not file_path.exists():
            raise CommandError(f'File not found: {file_path}')
        
        # Determine file format
        if file_path.suffix.lower() == '.json':
            framework_data = self.load_json_file(file_path)
        elif file_path.suffix.lower() in ['.yaml', '.yml']:
            framework_data = self.load_yaml_file(file_path)
        else:
            raise CommandError('Unsupported file format. Use .json, .yaml, or .yml files.')
        
        # Validate framework data
        self.validate_framework_data(framework_data)
        
        # Get user
        try:
            if options['user'] == 'system':
                user = None
            else:
                user = User.objects.get(username=options['user'])
        except User.DoesNotExist:
            raise CommandError(f'User not found: {options["user"]}')
        
        # Calculate file checksum for tracking changes
        file_checksum = self.calculate_file_checksum(file_path)
        
        if options['dry_run']:
            self.show_dry_run_summary(framework_data, file_checksum)
            return
        
        # Import framework
        try:
            with transaction.atomic():
                framework = self.import_framework_data(
                    framework_data, 
                    file_path, 
                    file_checksum, 
                    user, 
                    options['update']
                )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully imported framework: {framework.name} v{framework.version}'
                    )
                )
                self.stdout.write(f'Framework ID: {framework.id}')
                self.stdout.write(f'Total clauses imported: {framework.clause_count}')
                
        except Exception as e:
            raise CommandError(f'Failed to import framework: {str(e)}')
    
    def load_json_file(self, file_path):
        """Load framework data from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise CommandError(f'Invalid JSON file: {e}')
        except Exception as e:
            raise CommandError(f'Error reading file: {e}')
    
    def load_yaml_file(self, file_path):
        """Load framework data from YAML file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise CommandError(f'Invalid YAML file: {e}')
        except Exception as e:
            raise CommandError(f'Error reading file: {e}')
    
    def calculate_file_checksum(self, file_path):
        """Calculate SHA256 checksum of the file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    def validate_framework_data(self, data):
        """Validate that framework data has required fields."""
        required_fields = ['name', 'version', 'issuing_organization', 'effective_date']
        
        for field in required_fields:
            if field not in data:
                raise CommandError(f'Missing required field: {field}')
        
        # Validate clauses structure
        if 'clauses' in data and not isinstance(data['clauses'], list):
            raise CommandError('Clauses must be a list')
        
        # Validate each clause
        for i, clause in enumerate(data.get('clauses', [])):
            if not isinstance(clause, dict):
                raise CommandError(f'Clause {i} must be a dictionary')
            
            clause_required = ['clause_id', 'title', 'description']
            for field in clause_required:
                if field not in clause:
                    raise CommandError(f'Clause {i} missing required field: {field}')
    
    def show_dry_run_summary(self, framework_data, checksum):
        """Show what would be imported without actually importing."""
        self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
        self.stdout.write('-' * 50)
        
        self.stdout.write(f'Framework Name: {framework_data["name"]}')
        self.stdout.write(f'Version: {framework_data["version"]}')
        self.stdout.write(f'Issuing Organization: {framework_data["issuing_organization"]}')
        self.stdout.write(f'Effective Date: {framework_data["effective_date"]}')
        self.stdout.write(f'File Checksum: {checksum[:16]}...')
        
        clauses = framework_data.get('clauses', [])
        self.stdout.write(f'Total Clauses: {len(clauses)}')
        
        if clauses:
            self.stdout.write('\\nSample clauses:')
            for clause in clauses[:3]:  # Show first 3 clauses
                self.stdout.write(f'  - {clause["clause_id"]}: {clause["title"]}')
            
            if len(clauses) > 3:
                self.stdout.write(f'  ... and {len(clauses) - 3} more clauses')
    
    def import_framework_data(self, data, file_path, checksum, user, update_existing):
        """Import framework and clauses from validated data."""
        
        # Check if framework already exists
        existing_framework = Framework.objects.filter(
            name=data['name'], 
            version=data['version']
        ).first()
        
        if existing_framework and not update_existing:
            raise CommandError(
                f'Framework {data["name"]} v{data["version"]} already exists. '
                'Use --update to update existing framework.'
            )
        
        # Parse effective date
        effective_date = parse_date(data['effective_date'])
        if not effective_date:
            raise CommandError(f'Invalid effective_date format: {data["effective_date"]}')
        
        # Parse expiry date if provided
        expiry_date = None
        if 'expiry_date' in data and data['expiry_date']:
            expiry_date = parse_date(data['expiry_date'])
            if not expiry_date:
                raise CommandError(f'Invalid expiry_date format: {data["expiry_date"]}')
        
        # Create or update framework
        framework_defaults = {
            'short_name': data.get('short_name', data['name'][:50]),
            'description': data.get('description', ''),
            'framework_type': data.get('framework_type', 'security'),
            'external_id': data.get('external_id', ''),
            'issuing_organization': data['issuing_organization'],
            'official_url': data.get('official_url', ''),
            'effective_date': effective_date,
            'expiry_date': expiry_date,
            'status': data.get('status', 'active'),
            'is_mandatory': data.get('is_mandatory', False),
            'created_by': user,
            'imported_from': str(file_path),
            'import_checksum': checksum,
        }
        
        if existing_framework and update_existing:
            # Update existing framework
            for field, value in framework_defaults.items():
                if field != 'created_by':  # Don't change creator
                    setattr(existing_framework, field, value)
            existing_framework.save()
            framework = existing_framework
            
            # Clear existing clauses for update
            framework.clauses.all().delete()
            self.stdout.write('Updated existing framework')
        else:
            # Create new framework
            framework = Framework.objects.create(
                name=data['name'],
                version=data['version'],
                **framework_defaults
            )
            self.stdout.write('Created new framework')
        
        # Import clauses
        clauses_data = data.get('clauses', [])
        self.import_clauses(framework, clauses_data)
        
        return framework
    
    def import_clauses(self, framework, clauses_data):
        """Import clauses for the framework."""
        clause_objects = []
        clause_map = {}  # For handling parent-child relationships
        
        # Sort clauses by sort_order or clause_id for consistent processing
        sorted_clauses = sorted(
            clauses_data, 
            key=lambda x: (x.get('sort_order', 999), x['clause_id'])
        )
        
        # First pass: create all clauses without parent relationships
        for clause_data in sorted_clauses:
            clause = Clause(
                framework=framework,
                clause_id=clause_data['clause_id'],
                title=clause_data['title'],
                description=clause_data['description'],
                clause_type=clause_data.get('clause_type', 'control'),
                criticality=clause_data.get('criticality', 'medium'),
                is_testable=clause_data.get('is_testable', True),
                sort_order=clause_data.get('sort_order', 0),
                implementation_guidance=clause_data.get('implementation_guidance', ''),
                testing_procedures=clause_data.get('testing_procedures', ''),
                external_references=clause_data.get('external_references', {}),
            )
            clause_objects.append(clause)
            clause_map[clause_data['clause_id']] = clause
        
        # Bulk create clauses
        Clause.objects.bulk_create(clause_objects)
        
        # Second pass: update parent relationships
        clauses_with_parents = [
            c for c in sorted_clauses 
            if c.get('parent_clause_id')
        ]
        
        if clauses_with_parents:
            # Reload clauses from database to get IDs
            db_clauses = {
                c.clause_id: c for c in 
                Clause.objects.filter(framework=framework)
            }
            
            for clause_data in clauses_with_parents:
                parent_clause_id = clause_data['parent_clause_id']
                if parent_clause_id in db_clauses:
                    clause = db_clauses[clause_data['clause_id']]
                    clause.parent_clause = db_clauses[parent_clause_id]
                    clause.save()
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Parent clause {parent_clause_id} not found for {clause_data["clause_id"]}'
                        )
                    )
        
        self.stdout.write(f'Imported {len(clause_objects)} clauses')