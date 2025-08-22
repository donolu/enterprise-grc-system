import json
import yaml
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from catalogs.models import Framework


class Command(BaseCommand):
    help = 'Export compliance frameworks to structured JSON or YAML files'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'framework_id',
            type=int,
            help='Framework ID to export'
        )
        parser.add_argument(
            'output_path',
            type=str,
            help='Output file path (.json or .yaml/.yml)'
        )
        parser.add_argument(
            '--format',
            choices=['json', 'yaml'],
            help='Output format (auto-detected from file extension if not specified)'
        )
        parser.add_argument(
            '--include-metadata',
            action='store_true',
            help='Include creation timestamps and user info'
        )
        parser.add_argument(
            '--pretty',
            action='store_true',
            default=True,
            help='Pretty print the output (default: True)'
        )
    
    def handle(self, *args, **options):
        try:
            framework = Framework.objects.get(id=options['framework_id'])
        except Framework.DoesNotExist:
            raise CommandError(f'Framework with ID {options["framework_id"]} not found')
        
        output_path = Path(options['output_path'])
        
        # Determine output format
        format_choice = options.get('format')
        if not format_choice:
            if output_path.suffix.lower() == '.json':
                format_choice = 'json'
            elif output_path.suffix.lower() in ['.yaml', '.yml']:
                format_choice = 'yaml'
            else:
                raise CommandError('Cannot determine output format from file extension. Use --format')
        
        # Export framework data
        framework_data = self.export_framework(framework, options['include_metadata'])
        
        # Write to file
        if format_choice == 'json':
            self.write_json_file(framework_data, output_path, options['pretty'])
        else:
            self.write_yaml_file(framework_data, output_path)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully exported framework "{framework.name}" to {output_path}'
            )
        )
        self.stdout.write(f'Format: {format_choice.upper()}')
        self.stdout.write(f'Clauses exported: {len(framework_data["clauses"])}')
    
    def export_framework(self, framework, include_metadata):
        """Export framework to dictionary structure."""
        
        # Basic framework data
        data = {
            'name': framework.name,
            'short_name': framework.short_name,
            'version': framework.version,
            'description': framework.description,
            'framework_type': framework.framework_type,
            'external_id': framework.external_id,
            'issuing_organization': framework.issuing_organization,
            'official_url': framework.official_url,
            'effective_date': framework.effective_date.isoformat() if framework.effective_date else None,
            'expiry_date': framework.expiry_date.isoformat() if framework.expiry_date else None,
            'status': framework.status,
            'is_mandatory': framework.is_mandatory,
        }
        
        # Add metadata if requested
        if include_metadata:
            data['metadata'] = {
                'created_by': framework.created_by.username if framework.created_by else None,
                'created_at': framework.created_at.isoformat(),
                'updated_at': framework.updated_at.isoformat(),
                'imported_from': framework.imported_from,
                'import_checksum': framework.import_checksum,
            }
        
        # Export clauses
        data['clauses'] = []
        
        # Get all clauses ordered by sort_order and clause_id
        clauses = framework.clauses.order_by('sort_order', 'clause_id')
        
        for clause in clauses:
            clause_data = {
                'clause_id': clause.clause_id,
                'title': clause.title,
                'description': clause.description,
                'clause_type': clause.clause_type,
                'criticality': clause.criticality,
                'is_testable': clause.is_testable,
                'sort_order': clause.sort_order,
                'implementation_guidance': clause.implementation_guidance,
                'testing_procedures': clause.testing_procedures,
                'external_references': clause.external_references,
            }
            
            # Add parent clause ID if exists
            if clause.parent_clause:
                clause_data['parent_clause_id'] = clause.parent_clause.clause_id
            
            # Add metadata if requested
            if include_metadata:
                clause_data['metadata'] = {
                    'created_at': clause.created_at.isoformat(),
                    'updated_at': clause.updated_at.isoformat(),
                    'control_count': clause.control_count,
                }
            
            data['clauses'].append(clause_data)
        
        return data
    
    def write_json_file(self, data, output_path, pretty):
        """Write data to JSON file."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                if pretty:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                else:
                    json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            raise CommandError(f'Error writing JSON file: {e}')
    
    def write_yaml_file(self, data, output_path):
        """Write data to YAML file."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    data, 
                    f, 
                    default_flow_style=False, 
                    allow_unicode=True,
                    sort_keys=False
                )
        except Exception as e:
            raise CommandError(f'Error writing YAML file: {e}')