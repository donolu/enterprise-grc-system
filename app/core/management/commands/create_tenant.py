from django.core.management.base import BaseCommand
from core.models import Tenant, Domain

class Command(BaseCommand):
    help = 'Create a new tenant'

    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='Tenant name')
        parser.add_argument('slug', type=str, help='Tenant slug (for schema name)')
        parser.add_argument('domain', type=str, help='Domain name')

    def handle(self, *args, **options):
        name = options['name']
        slug = options['slug']
        domain_name = options['domain']
        
        # Create tenant
        tenant = Tenant.objects.create(
            name=name,
            slug=slug,
            schema_name=slug
        )
        
        # Create domain
        domain = Domain.objects.create(
            domain=domain_name,
            tenant=tenant,
            is_primary=True
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created tenant "{name}" with domain "{domain_name}"'
            )
        )
        
        # Run migrations for this tenant
        self.stdout.write('Running migrations for new tenant...')
        from django.core.management import call_command
        call_command('migrate_schemas', schema_name=slug)