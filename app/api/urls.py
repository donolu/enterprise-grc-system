from django.urls import path, include

urlpatterns = [
    path('auth/', include('authn.urls')),
    path('assets/', include('assets.urls')),
    path('calendar/', include('calendarhub.urls')),
    path('catalogs/', include('catalogs.urls')),
    path('compliance/', include('compliance.urls')),
    path('exports/', include('exports.urls')),
    path('risk/', include('risk.urls')),
    path('policies/', include('policies.urls')),
    path('training/', include('training.urls')),
    path('knowledge/', include('knowledge.urls')),
    path('analytics/', include('analytics.urls')),
    path('vendors/', include('vendors.urls')),
    path('vuln/', include('vuln.urls')),
    path('', include('api.routers')),
]
