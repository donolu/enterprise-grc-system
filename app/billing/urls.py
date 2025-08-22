from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import approval_views

router = DefaultRouter()
router.register(r'plans', views.PlanViewSet)
router.register(r'billing', views.BillingViewSet, basename='billing')
router.register(r'limit-overrides', approval_views.LimitOverrideRequestViewSet, basename='limit-overrides')

urlpatterns = [
    path('api/', include(router.urls)),
    path('webhooks/stripe/', views.StripeWebhookView.as_view(), name='stripe_webhook'),
]