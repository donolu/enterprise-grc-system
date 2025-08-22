from django.urls import path, include

urlpatterns = [
    path('auth/', include('authn.urls')),
    path('catalogs/', include('catalogs.urls')),
    path('', include('api.routers')),
]
