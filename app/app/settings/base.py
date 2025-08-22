import os
from pathlib import Path
from dotenv import load_dotenv
from celery.schedules import crontab

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]
SECRET_KEY = os.environ["SECRET_KEY"]
DEBUG = bool(int(os.environ.get("DEBUG", "0")))

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core", # Moved core here
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "django_otp",
    "django_otp.plugins.otp_email",
    "authn",
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

AUTH_USER_MODEL = "core.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "core.middleware.TenantResolveMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "app.urls"
WSGI_APPLICATION = "app.wsgi.application"
ASGI_APPLICATION = "app.asgi.application"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"
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
        "ENGINE": "django.db.backends.postgresql",
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

SPECTACULAR_SETTINGS = {"TITLE": "GRC SaaS API", "VERSION": "0.1"}

CELERY_BROKER_URL = os.environ["CELERY_BROKER_URL"]
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST","localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT","1025"))
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL","noreply@example.com")

SITE_DOMAIN = os.environ.get("SITE_DOMAIN","localhost:8000")

CELERY_BEAT_SCHEDULE = {
    "assessments_due_reminders_daily": {
        "task": "compliance.tasks.send_due_reminders",
        "schedule": crontab(hour=8, minute=0), 
    },
}

