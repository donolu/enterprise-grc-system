from django.urls import resolve, reverse

from vendors.views import VendorViewSet


def test_vendor_api_routes_are_mounted():
    assert reverse("vendor-list") == "/api/vendors/vendors/"
    assert reverse("vendor-choices") == "/api/vendors/vendors/choices/"
    assert resolve("/api/vendors/vendors/").func.cls is VendorViewSet
