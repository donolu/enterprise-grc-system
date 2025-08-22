from django.urls import path, include

urlpatterns = [
    path('auth/', include('authn.urls')),
    path('', include('api.routers')),
]
