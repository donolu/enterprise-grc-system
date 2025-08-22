import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.core.management import call_command
from catalogs.models import Framework


class Command(BaseCommand):
    help = 'Load all framework fixtures from the fixtures/frameworks directory'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing frameworks if they already exist'
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Username of user importing the frameworks',
            default='system'
        )
    
    def handle(self, *args, **options):
        # Get the fixtures directory
        fixtures_dir = Path(__file__).parent.parent.parent / 'fixtures' / 'frameworks'
        
        if not fixtures_dir.exists():
            self.stdout.write(
                self.style.ERROR(f'Fixtures directory not found: {fixtures_dir}')
            )
            return
        
        # Find all JSON framework files
        framework_files = list(fixtures_dir.glob('*.json'))
        
        if not framework_files:
            self.stdout.write(
                self.style.WARNING(f'No framework files found in {fixtures_dir}')
            )
            return
        
        self.stdout.write(f'Found {len(framework_files)} framework files to import:')
        for file_path in framework_files:
            self.stdout.write(f'  - {file_path.name}')
        
        self.stdout.write('')
        
        # Import each framework file
        success_count = 0
        error_count = 0
        
        for file_path in framework_files:
            try:
                self.stdout.write(f'Importing {file_path.name}...')
                
                # Use the import_framework command
                call_command(
                    'import_framework',
                    str(file_path),
                    update=options['update'],
                    user=options['user'],
                    verbosity=0  # Reduce verbosity to avoid duplicate output
                )
                
                success_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Successfully imported {file_path.name}')
                )
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Failed to import {file_path.name}: {str(e)}')
                )
        
        # Summary
        self.stdout.write('')
        self.stdout.write('Import Summary:')
        self.stdout.write(f'  Successful: {success_count}')
        self.stdout.write(f'  Errors: {error_count}')
        self.stdout.write(f'  Total frameworks in database: {Framework.objects.count()}')
        
        if success_count > 0:
            self.stdout.write(
                self.style.SUCCESS('Framework fixtures loaded successfully!')
            )
        
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING('Some frameworks failed to import. Check errors above.')
            )