from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VendorViewSet, VendorCategoryViewSet, VendorContactViewSet,
    VendorServiceViewSet, VendorNoteViewSet, VendorTaskViewSet
)

router = DefaultRouter()
router.register(r'vendors', VendorViewSet, basename='vendor')
router.register(r'categories', VendorCategoryViewSet, basename='vendorcategory')
router.register(r'contacts', VendorContactViewSet, basename='vendorcontact')
router.register(r'services', VendorServiceViewSet, basename='vendorservice')
router.register(r'notes', VendorNoteViewSet, basename='vendornote')
router.register(r'tasks', VendorTaskViewSet, basename='vendortask')

urlpatterns = [
    path('', include(router.urls)),
]