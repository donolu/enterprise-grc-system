#!/bin/bash

# Startup script for production deployment
# Handles migrations, static files, and server startup

set -e  # Exit on any error

echo "🚀 Starting GRC Platform deployment..."
echo "Environment: ${DJANGO_SETTINGS_MODULE:-app.settings.production}"
echo "Time: $(date)"

# Change to app directory
cd /workspace/app

# Function to run migrations
run_migrations() {
    echo "📋 Running database migrations..."
    migration_database_url="${DIRECT_DATABASE_URL:-${DATABASE_URL:-}}"
    
    # First, run shared schema migrations
    echo "Running shared schema migrations..."
    if [[ -n "$migration_database_url" ]]; then
        DATABASE_URL="$migration_database_url" python manage.py migrate_schemas --shared
    else
        python manage.py migrate_schemas --shared
    fi
    
    # Check if we have any existing tenants and run their migrations
    echo "Running tenant schema migrations..."
    if [[ -n "$migration_database_url" ]]; then
        DATABASE_URL="$migration_database_url" python manage.py migrate_schemas --tenant
    else
        python manage.py migrate_schemas --tenant
    fi
    
    echo "✅ Migrations completed successfully"
}

# Function to collect static files
collect_static() {
    if [[ "${DJANGO_SETTINGS_MODULE}" == *"production"* ]]; then
        echo "📁 Collecting static files for production..."
        python manage.py collectstatic --noinput --clear
        echo "✅ Static files collected"
    else
        echo "⏭️ Skipping static file collection (not production)"
    fi
}

# Function to create superuser if needed
create_superuser() {
    if [[ "${CREATE_SUPERUSER}" == "true" ]]; then
        if [[ -z "${SUPERUSER_PASSWORD}" ]]; then
            echo "❌ SUPERUSER_PASSWORD must be set when CREATE_SUPERUSER=true"
            exit 1
        fi

        echo "👤 Creating superuser..."
        python manage.py shell << EOF
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()
username = '${SUPERUSER_USERNAME:-admin}'
email = '${SUPERUSER_EMAIL:-admin@example.com}'
password = '${SUPERUSER_PASSWORD}'

try:
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username=username, email=email, password=password)
        print(f"✅ Superuser '{username}' created successfully")
    else:
        print(f"ℹ️ Superuser '{username}' already exists")
except Exception as e:
    print(f"❌ Error creating superuser: {e}")
EOF
    fi
}

# Function to create default tenant if needed
create_default_tenant() {
    if [[ "${CREATE_DEFAULT_TENANT}" == "true" ]]; then
        echo "🏢 Creating default tenant..."
        python manage.py shell << EOF
from core.models import Tenant, Domain

# Create default tenant if it doesn't exist
tenant_name = '${DEFAULT_TENANT_NAME:-Default Company}'
tenant_slug = '${DEFAULT_TENANT_SLUG:-default}'
tenant_schema = '${DEFAULT_TENANT_SCHEMA:-default}'
domain_name = '${DEFAULT_TENANT_DOMAIN:-default.localhost}'

try:
    tenant, created = Tenant.objects.get_or_create(
        schema_name=tenant_schema,
        defaults={'name': tenant_name, 'slug': tenant_slug}
    )
    
    if created:
        print(f"✅ Created tenant: {tenant_name}")
    else:
        print(f"ℹ️ Tenant already exists: {tenant_name}")
    
    # Create domain
    domain, created = Domain.objects.get_or_create(
        domain=domain_name,
        defaults={'tenant': tenant, 'is_primary': True}
    )
    
    if created:
        print(f"✅ Created domain: {domain_name}")
    else:
        print(f"ℹ️ Domain already exists: {domain_name}")
        
except Exception as e:
    print(f"❌ Error creating tenant: {e}")
EOF
    fi
}

# Function to setup initial data
setup_initial_data() {
    if [[ "${SETUP_INITIAL_DATA}" == "true" ]]; then
        echo "🔧 Setting up initial data..."
        
        # Create subscription plans
        python manage.py shell << EOF
from core.models import Plan

plans_data = [
    {
        'name': 'Free',
        'slug': 'free',
        'description': 'Perfect for getting started',
        'price_monthly': 0,
        'max_users': 3,
        'max_documents': 50,
        'max_frameworks': 1,
        'has_api_access': False,
        'has_advanced_reporting': False,
        'has_priority_support': False,
    },
    {
        'name': 'Basic',
        'slug': 'basic',
        'description': 'Ideal for small to medium teams',
        'price_monthly': 49,
        'max_users': 10,
        'max_documents': 500,
        'max_frameworks': 5,
        'has_api_access': True,
        'has_advanced_reporting': False,
        'has_priority_support': False,
    },
    {
        'name': 'Enterprise',
        'slug': 'enterprise',
        'description': 'Full-featured solution for large organizations',
        'price_monthly': 199,
        'max_users': 100,
        'max_documents': 10000,
        'max_frameworks': 999,
        'has_api_access': True,
        'has_advanced_reporting': True,
        'has_priority_support': True,
    }
]

for plan_data in plans_data:
    plan, created = Plan.objects.get_or_create(
        slug=plan_data['slug'],
        defaults=plan_data
    )
    if created:
        print(f"✅ Created plan: {plan.name}")
    else:
        print(f"ℹ️ Plan already exists: {plan.name}")
EOF
        
        echo "✅ Initial data setup completed"
    fi
}

# Function to validate environment
validate_environment() {
    echo "🔍 Validating environment..."
    
    if [[ -n "${DATABASE_URL}" ]]; then
        required_vars=("SECRET_KEY" "DATABASE_URL")
    else
        required_vars=(
            "SECRET_KEY"
            "POSTGRES_DB"
            "POSTGRES_USER"
            "POSTGRES_PASSWORD"
            "POSTGRES_HOST"
        )
    fi

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            echo "❌ Missing required environment variable: $var"
            exit 1
        fi
    done
    
    # Test database connection
    echo "Testing database connection..."
    python manage.py dbshell --command="SELECT 1;" > /dev/null 2>&1
    if [[ $? -eq 0 ]]; then
        echo "✅ Database connection successful"
    else
        echo "❌ Database connection failed"
        exit 1
    fi
}

# Function to run health checks
run_health_checks() {
    echo "🏥 Running health checks..."
    
    # Django system check
    echo "Running Django system checks..."
    python manage.py check --deploy
    
    echo "✅ Health checks completed"
}

# Main execution flow
main() {
    echo "Starting deployment sequence..."
    
    # Always validate environment first
    validate_environment
    
    # Run migrations if specified or if RUN_MIGRATIONS is true
    if [[ "${RUN_MIGRATIONS}" == "true" ]] || [[ "$1" == "--migrate" ]]; then
        run_migrations
    else
        echo "⏭️ Skipping migrations (set RUN_MIGRATIONS=true to enable)"
    fi
    
    # Collect static files for production
    collect_static
    
    # Create superuser if specified
    create_superuser
    
    # Create default tenant if specified
    create_default_tenant
    
    # Setup initial data if specified
    setup_initial_data
    
    # Run health checks
    run_health_checks
    
    echo "✅ Startup sequence completed successfully!"
    echo "🚀 Ready to start server..."
    
    # If this script is run directly (not sourced), start the server
    if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
        echo "Starting Gunicorn server..."
        exec gunicorn app.wsgi:application \
            --bind 0.0.0.0:${PORT:-8000} \
            --workers ${WORKERS:-2} \
            --worker-class ${WORKER_CLASS:-sync} \
            --worker-connections ${WORKER_CONNECTIONS:-1000} \
            --max-requests ${MAX_REQUESTS:-1000} \
            --max-requests-jitter ${MAX_REQUESTS_JITTER:-100} \
            --timeout ${TIMEOUT:-30} \
            --keep-alive ${KEEP_ALIVE:-2} \
            --access-logfile - \
            --error-logfile - \
            --log-level ${LOG_LEVEL:-info}
    fi
}

# Handle script arguments
case "$1" in
    --migrate-only)
        validate_environment
        run_migrations
        ;;
    --setup-only)
        validate_environment
        create_superuser
        create_default_tenant
        setup_initial_data
        ;;
    --health-check)
        run_health_checks
        ;;
    *)
        main "$@"
        ;;
esac
