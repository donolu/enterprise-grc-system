from django.apps import AppConfig


class VendorsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'vendors'
    verbose_name = 'Vendor Management'
    
    def ready(self):
        """Import signals when app is ready."""
        try:
            import vendors.signals  # noqa
        except ImportError:
            pass