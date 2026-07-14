"""
Test settings for CI/CD pipeline and automated testing.
"""

from .base import *
import tempfile

# Override for faster testing
DEBUG = False
TESTING = True

# The suite still has a mix of tenant-aware tests and legacy plain TestCase
# tests. Keep all installed apps available in both schemas under test so the
# tenant router does not hide tenant app tables from public-schema tests.
SHARED_APPS = INSTALLED_APPS
TENANT_APPS = INSTALLED_APPS

# Use in-memory cache for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Test database configuration
DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",
        "NAME": os.environ.get("POSTGRES_DB", "grc_test"),
        "USER": os.environ.get("POSTGRES_USER", "grc"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "TEST": {
            "NAME": os.environ.get("POSTGRES_TEST_DB", "test_grc"),
        },
    }
}

# Disable migrations for faster testing (optional)
# class DisableMigrations:
#     def __contains__(self, item):
#         return True
#     def __getitem__(self, item):
#         return None
# 
# MIGRATION_MODULES = DisableMigrations()

# Use console email backend for tests
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable Celery for tests - run tasks synchronously
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use temporary directory for media files
MEDIA_ROOT = tempfile.mkdtemp()

# Simplified logging for tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
        'app': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}

# Faster password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Test-specific security settings
SECRET_KEY = os.environ.get('SECRET_KEY', 'test-secret-key-not-for-production')

# Allow all hosts in test
ALLOWED_HOSTS = ['*']

# Disable CSRF for API tests
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# Test Azure Storage settings (using Azurite)
AZURE_STORAGE_CONNECTION_STRING = os.environ.get(
    'AZURE_STORAGE_CONNECTION_STRING',
    'UseDevelopmentStorage=true'
)

# Stripe test mode (don't make real API calls in tests unless specified)
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', 'fake-stripe-secret-key-for-testing')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', 'fake-stripe-publishable-key-for-testing')

# Test-specific feature flags
TESTING_SKIP_STRIPE_CALLS = True
TESTING_SKIP_EMAIL_SENDING = True

# Django Rest Framework test settings
REST_FRAMEWORK.update({
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'DEFAULT_THROTTLE_RATES': {
        'anon': '10000/hour',
        'user': '10000/hour',
        'auth': '10000/minute',
        'two_factor': '10000/minute',
        'exports': '10000/hour',
        'evidence_upload': '10000/hour',
    },
})

# Spectacular settings for API docs testing
SPECTACULAR_SETTINGS.update({
    'SERVE_INCLUDE_SCHEMA': False,  # Don't serve schema in tests
})

print("Using test settings - database:", DATABASES['default']['NAME'])
