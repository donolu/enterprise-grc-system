"""
Test settings for CI/CD pipeline and automated testing.
"""

from .base import *
import tempfile

# Override for faster testing
DEBUG = False
TESTING = True

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
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "grc"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "TEST": {
            "NAME": "test_grc",
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
    'DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://localhost:10000/devstoreaccount1;'
)

# Stripe test mode (don't make real API calls in tests unless specified)
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_fake_key_for_testing')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', 'pk_test_fake_key_for_testing')

# Test-specific feature flags
TESTING_SKIP_STRIPE_CALLS = True
TESTING_SKIP_EMAIL_SENDING = True

# Django Rest Framework test settings
REST_FRAMEWORK.update({
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
})

# Spectacular settings for API docs testing
SPECTACULAR_SETTINGS.update({
    'SERVE_INCLUDE_SCHEMA': False,  # Don't serve schema in tests
})

print("Using test settings - database:", DATABASES['default']['NAME'])