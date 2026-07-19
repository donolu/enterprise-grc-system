"""
Production settings for container deployments.
"""

from .base import *
from .base import _database_config_from_url


def _csv_env(name):
    return [
        value.strip()
        for value in os.environ.get(name, '').split(',')
        if value.strip()
    ]

# Security settings
DEBUG = False
ALLOWED_HOSTS = [
    '.azurewebsites.net',
    os.environ.get('CUSTOM_DOMAIN', ''),
    os.environ.get('PUBLIC_HOSTNAME', ''),
    os.environ.get('RENDER_EXTERNAL_HOSTNAME', ''),
] + [host.strip() for host in os.environ.get('ADDITIONAL_HOSTS', '').split(',') if host.strip()]
ALLOWED_HOSTS = [host for host in ALLOWED_HOSTS if host]

CORS_ALLOWED_ORIGINS = _csv_env('CORS_ALLOWED_ORIGINS')
CSRF_TRUSTED_ORIGINS = _csv_env('CSRF_TRUSTED_ORIGINS') or CORS_ALLOWED_ORIGINS

# Database configuration. Prefer DATABASE_URL so the same image runs on Render,
# DigitalOcean, AWS, Azure, or self-hosted Postgres.
if os.environ.get('DATABASE_URL'):
    DATABASES = {'default': _database_config_from_url(os.environ['DATABASE_URL'])}
    DATABASES['default'].setdefault('OPTIONS', {})
    DATABASES['default']['OPTIONS'].setdefault(
        'sslmode',
        os.environ.get('DATABASE_SSLMODE', 'require'),
    )
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django_tenants.postgresql_backend',
            'NAME': os.environ.get('POSTGRES_DB', 'grc'),
            'USER': os.environ.get('POSTGRES_USER', 'grc'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
            'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
            'PORT': os.environ.get('POSTGRES_PORT', '5432'),
            'OPTIONS': {
                'sslmode': os.environ.get('DATABASE_SSLMODE', 'require'),
            },
            'CONN_MAX_AGE': 60,
        }
    }

DATABASES['default']['CONN_MAX_AGE'] = int(os.environ.get('DATABASE_CONN_MAX_AGE', '60'))

# Cache configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
    }
}

# Session storage (use database for reliability)
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_CACHE_ALIAS = 'default'

# Email configuration for production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.sendgrid.net')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@yourcompany.com')

# Security settings for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# HTTPS settings
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True').lower() == 'true'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Cookies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# Logging configuration
_log_handlers = {
    'console': {
        'class': 'logging.StreamHandler',
        'formatter': 'verbose',
    },
}
if os.environ.get('DJANGO_LOG_FILE'):
    _log_handlers['file'] = {
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': os.environ['DJANGO_LOG_FILE'],
        'maxBytes': 1024*1024*15,  # 15MB
        'backupCount': 10,
        'formatter': 'verbose',
    }

_handler_names = list(_log_handlers)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': _log_handlers,
    'root': {
        'handlers': _handler_names,
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': _handler_names,
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}

# Celery configuration for production
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True

# Performance settings
CONN_MAX_AGE = 60
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50MB

# Health check settings
HEALTH_CHECK_ENABLED = True

# Metrics are useful in production, but must not be exposed publicly by default.
METRICS_BEARER_TOKEN = os.environ.get('METRICS_BEARER_TOKEN', '')
METRICS_ENABLED = (
    os.environ.get('METRICS_ENABLED', '1').lower() == 'true'
    or os.environ.get('METRICS_ENABLED', '1') == '1'
) and bool(METRICS_BEARER_TOKEN)

# Stripe production settings
STRIPE_LIVE_MODE = os.environ.get('STRIPE_LIVE_MODE', 'False').lower() == 'true'
if STRIPE_LIVE_MODE:
    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_LIVE_PUBLISHABLE_KEY', STRIPE_PUBLISHABLE_KEY)
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_LIVE_SECRET_KEY', STRIPE_SECRET_KEY)
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_LIVE_WEBHOOK_SECRET', STRIPE_WEBHOOK_SECRET)

# Run migrations on startup if specified
RUN_MIGRATIONS = os.environ.get('RUN_MIGRATIONS', 'False').lower() == 'true'
