from django.apps import AppConfig


class CatalogsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'catalogs'
    verbose_name = 'Framework & Control Catalogs'
    
    def ready(self):
        # Import signal handlers if any
        pass