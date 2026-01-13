from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views.viewsets import (
    ShipmentViewSet,
    UploadSessionViewSet,
    SavedAddressViewSet,
    SavedPackageViewSet,
)
from .views.upload import UploadCSVView  # keep legacy single-route alias
from .views.checkout import CheckoutView
from .views.review import ShipmentEditView
from .views.purchase import PurchaseView

router = DefaultRouter()
router.register(r'shipments', ShipmentViewSet, basename='shipment')
router.register(r'uploads', UploadSessionViewSet, basename='upload')
router.register(r'saved-addresses', SavedAddressViewSet, basename='savedaddress')
router.register(r'saved-packages', SavedPackageViewSet, basename='savedpackage')

urlpatterns = [
    # router-backed resource endpoints
    path('', include(router.urls)),
    # path('uploads', UploadCSVView.as_view(), name='upload-csv'),
    # Purchase endpoint (RESTful naming)
    path('uploads/<uuid:upload_session_id>/purchase/', CheckoutView.as_view(), name='uploadsession-purchase'),
    path('uploads/<uuid:upload_session_id>/purchase', PurchaseView.as_view(), name='upload-purchase'),

    # Labels retrieval endpoint (implement UploadSessionLabelsView)
    # path('uploads/<uuid:upload_session_id>/labels/', UploadSessionLabelsView.as_view(), name='uploadsession-labels'),
    # Optionally, a unified bulk update endpoint (implement if needed)
    # path('shipments/bulk-update/', BulkUpdateShipmentsView.as_view(), name='shipments-bulk-update'),
    path('shipments/<int:shipment_id>', ShipmentEditView.as_view(), name='shipment-edit'),
]