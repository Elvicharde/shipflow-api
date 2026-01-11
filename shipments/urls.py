from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views.viewsets import (
    ShipmentViewSet,
    UploadSessionViewSet,
    SavedAddressViewSet,
    SavedPackageViewSet,
)
from .views.upload import UploadCSVView  # keep legacy single-route alias

router = DefaultRouter()
router.register(r'shipments', ShipmentViewSet, basename='shipment')
router.register(r'uploads', UploadSessionViewSet, basename='upload')
router.register(r'saved-addresses', SavedAddressViewSet, basename='savedaddress')
router.register(r'saved-packages', SavedPackageViewSet, basename='savedpackage')

urlpatterns = [
    # legacy upload endpoint (kept for compatibility)
    path('upload/', UploadCSVView.as_view(), name='upload-csv'),
    # router-backed resource endpoints
    path('', include(router.urls)),
]