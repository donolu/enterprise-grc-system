import os
from celery import Celery

from core.observability import register_celery_metrics

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings.local")
celery_app = Celery("grc")
celery_app.config_from_object("django.conf:settings", namespace="CELERY")
celery_app.autodiscover_tasks()
register_celery_metrics()
