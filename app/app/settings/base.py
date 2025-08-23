import os
from pathlib import Path
from dotenv import load_dotenv
from celery.schedules import crontab

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]
SECRET_KEY = os.environ["SECRET_KEY"]
DEBUG = bool(int(os.environ.get("DEBUG", "0")))

ALLOWED_HOSTS = ["*"]

SHARED_APPS = [
    "django_tenants", # Must be first
    "django.contrib.admin",
    "django.contrib.auth", 
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters", 
    "drf_spectacular",
    "core", # Needed here for Tenant and Domain models
]

TENANT_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes", 
    "django.contrib.sessions",
    "django.contrib.messages",
    "django_otp",
    "django_otp.plugins.otp_email",
    "django_otp.plugins.otp_totp",
    "core", 
    "authn",
    "billing",
    "catalogs",
    "compliance",
    "risk",
    "vendors",
    "policies",
    "training",
    "vuln",
    "events",
    "audit",
    "exports",
    "search",
    "api",
]

INSTALLED_APPS = list(SHARED_APPS) + list(
    [app for app in TENANT_APPS if app not in SHARED_APPS]
)

AUTH_USER_MODEL = "core.User"

MIDDLEWARE = [
    "django_tenants.middleware.main.TenantMainMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "app.urls"
WSGI_APPLICATION = "app.wsgi.application"
ASGI_APPLICATION = "app.asgi.application"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"
# File Storage Configuration
# Using Azure Blob Storage with Azurite for development
DEFAULT_FILE_STORAGE = 'core.storage.TenantAwareBlobStorage'

# Azure Storage settings (configured but not used in development due to Azurite connectivity)
AZURE_STORAGE_CONNECTION_STRING = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')

# Media files configuration
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",
        "NAME": os.environ.get("POSTGRES_DB","grc"),
        "USER": os.environ.get("POSTGRES_USER","grc"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD","grc"),
        "HOST": os.environ.get("POSTGRES_HOST","postgres"),
        "PORT": os.environ.get("POSTGRES_PORT","5432"),
    }
}

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "GRC SaaS API",
    "DESCRIPTION": """
    Comprehensive API for Governance, Risk, and Compliance (GRC) management.
    
    This API provides complete functionality for compliance framework management,
    control assessments, evidence collection, reporting, and automated reminders.
    
    ## Features
    - **Framework Management**: Import and manage compliance frameworks (ISO 27001, NIST CSF, SOC 2, etc.)
    - **Assessment Workflow**: Complete control assessment lifecycle with status tracking
    - **Evidence Management**: Upload, link, and organize evidence with bulk operations
    - **Automated Reporting**: Generate professional PDF reports for audits and compliance
    - **Smart Reminders**: Configurable email notifications for due dates and overdue items
    - **Multi-tenant Architecture**: Complete tenant isolation with secure data scoping
    
    ## Authentication
    This API uses session-based authentication. Users must be authenticated to access endpoints.
    
    ## Tenant Scoping
    All data is automatically scoped to the authenticated user's tenant. Cross-tenant access is prevented.
    """,
    "VERSION": "1.0.0",
    "CONTACT": {
        "name": "GRC SaaS Support",
        "email": "support@grcsaas.com",
    },
    "LICENSE": {
        "name": "Proprietary",
    },
    # OpenAPI 3.0 configuration
    "OAS_VERSION": "3.0.3",
    "USE_SESSION_AUTH": True,
    "SCHEMA_PATH_PREFIX": "/api/",
    "COMPONENT_SPLIT_REQUEST": True,
    "SORT_OPERATIONS": False,
    
    # Enhanced documentation
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": None,
    "REDOC_DIST": "SIDECAR",
    
    # Security schemes
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "SessionAuth": {
                "type": "apiKey",
                "in": "cookie",
                "name": "sessionid",
                "description": "Django session authentication"
            }
        }
    },
    "SECURITY": [{"SessionAuth": []}],
    
    # Tags for organizing endpoints
    "TAGS": [
        {
            "name": "Authentication",
            "description": "User authentication and session management"
        },
        {
            "name": "Frameworks",
            "description": "Compliance framework management (ISO 27001, NIST CSF, SOC 2, etc.)"
        },
        {
            "name": "Clauses",
            "description": "Framework clause management and hierarchy"
        },
        {
            "name": "Controls",
            "description": "Control definition and management"
        },
        {
            "name": "Assessments",
            "description": "Control assessment workflow and lifecycle management"
        },
        {
            "name": "Evidence",
            "description": "Evidence collection, management, and linking"
        },
        {
            "name": "Reports",
            "description": "Assessment reporting and PDF generation"
        },
        {
            "name": "Documents",
            "description": "File upload and document management"
        },
        {
            "name": "Billing",
            "description": "Subscription and billing management"
        }
    ],
    
    # Custom preprocessing for better documentation
    "PREPROCESSING_HOOKS": [],
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
    ],
    
    # Enum choices handling
    "ENUM_NAME_OVERRIDES": {
        "StatusEnum": "catalogs.models.ControlAssessment.STATUS_CHOICES",
        "ImplementationStatusEnum": "catalogs.models.ControlAssessment.IMPLEMENTATION_STATUS_CHOICES",
        "EvidenceTypeEnum": "catalogs.models.ControlEvidence.EVIDENCE_TYPES",
        "ReminderTypeEnum": "catalogs.models.AssessmentReminderLog.REMINDER_TYPES",
    },
    
    # Error response schemas
    "DEFAULT_ERROR_RESPONSE_SCHEMA": "drf_spectacular.openapi.ErrorResponseSerializer",
}

CELERY_BROKER_URL = os.environ["CELERY_BROKER_URL"]
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST","localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT","1025"))
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL","noreply@example.com")

SITE_DOMAIN = os.environ.get("SITE_DOMAIN","localhost:8000")

CELERY_BEAT_SCHEDULE = {
    "assessments_due_reminders_daily": {
        "task": "catalogs.tasks.send_due_reminders",
        "schedule": crontab(hour=8, minute=0),  # 8 AM daily
    },
    "cleanup_reminder_logs_weekly": {
        "task": "catalogs.tasks.cleanup_old_reminder_logs",
        "schedule": crontab(hour=2, minute=0, day_of_week=0),  # 2 AM every Sunday
    },
}

# Stripe Configuration
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
STRIPE_PRICE_FREE = os.environ.get("STRIPE_PRICE_FREE")
STRIPE_PRICE_BASIC = os.environ.get("STRIPE_PRICE_BASIC")
STRIPE_PRICE_ENTERPRISE = os.environ.get("STRIPE_PRICE_ENTERPRISE")

# Limit Override Approval Settings
LIMIT_OVERRIDE_APPROVER_EMAILS = [
    email.strip() for email in os.environ.get("LIMIT_OVERRIDE_APPROVER_EMAILS", "admin@example.com").split(",")
    if email.strip()
]
ADMIN_NOTIFICATION_EMAILS = [
    email.strip() for email in os.environ.get("ADMIN_NOTIFICATION_EMAILS", "admin@example.com").split(",")
    if email.strip()
]

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Session settings
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# CSRF settings
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# Django-tenants settings
DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)
TENANT_MODEL = "core.Tenant"
TENANT_DOMAIN_MODEL = "core.Domain" 
PUBLIC_SCHEMA_URLCONF = "app.public_urls"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

