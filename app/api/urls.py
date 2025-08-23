from django.urls import path, include

urlpatterns = [
    path('auth/', include('authn.urls')),
    path('catalogs/', include('catalogs.urls')),
    path('exports/', include('exports.urls')),
    path('risk/', include('risk.urls')),
    path('', include('api.routers')),
]
