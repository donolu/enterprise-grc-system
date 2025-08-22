from django.contrib import admin
from django.urls import path, include

# Public schema URLs (for tenant management, etc.)
urlpatterns = [
    path('admin/', admin.site.urls),
    # Add public API endpoints here if needed
]