from __future__ import annotations

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from ..models import Shipment, UploadSession, SavedAddress, SavedPackage
from ..serializers.shipment import ShipmentReadSerializer, ShipmentWriteSerializer
from ..serializers.saved import SavedAddressSerializer, SavedPackageSerializer
from ..serializers.upload_session import UploadSessionSerializer
from ..serializers.bulk import (
    BulkUpdateServiceSerializer,
    BulkUpdateShipFromSerializer,
    BulkUpdatePackageSerializer,
    BulkDeleteSerializer,
)
from ..services.bulk_ops import (
    assign_shipping_service,
    update_shipping_service,
    update_ship_from,
    update_package,
    delete_shipments,
)
from ..services.session import upload_session_summary
from ..services.upload import process_csv_upload
from ..services.checkout import process_checkout

class ShipmentViewSet(viewsets.ModelViewSet):
    """
    CRUD + bulk actions for shipments.
    - detail action `assign-service` -> POST /shipments/{pk}/assign-service/
    - list-level bulk actions under /shipments/bulk/...
    """
    queryset = Shipment.objects.select_related("ship_from", "ship_to", "package").all()
    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return ShipmentWriteSerializer
        return ShipmentReadSerializer
    
    @action(detail=True, methods=["get"], url_path="by-session")
    def by_session(self, request, pk=None):
        """
        Get a single shipment by upload_session_id (from pk) and shipment_id (from query params), with optional filters.
        Usage: /shipments/{pk}/by-session/?shipment_id=...&status=...&order_number=...
        """
        shipment_id = request.query_params.get("shipment_id")
        if not pk or not shipment_id:
            return Response({"detail": "upload_session_id (pk) and shipment_id are required"}, status=status.HTTP_400_BAD_REQUEST)

        qs = Shipment.objects.filter(upload_session__id=pk, id=shipment_id)

        # Optional query param filtering
        status_param = request.query_params.get("status")
        ship_from_name = request.query_params.get("ship_from_name")
        ship_to_name = request.query_params.get("ship_to_name")
        order_number = request.query_params.get("order_number")

        if status_param:
            qs = qs.filter(status=status_param)
        if ship_from_name:
            qs = qs.filter(ship_from__name__icontains=ship_from_name)
        if ship_to_name:
            qs = qs.filter(ship_to__name__icontains=ship_to_name)
        if order_number:
            qs = qs.filter(order_number__icontains=order_number)

        shipment = qs.first()
        if not shipment:
            return Response({"detail": "Shipment not found"}, status=status.HTTP_404_NOT_FOUND)

        fields = request.query_params.get("fields")
        if fields in ["ship_from", "ship_to", "package"]:
            # Return only the requested part
            data = getattr(shipment, fields, None)
            if data is None:
                return Response({"detail": f"Field '{fields}' not found on shipment."}, status=status.HTTP_400_BAD_REQUEST)
            # If it's a related object, serialize it
            from ..serializers.shipment import AddressSerializer, PackageSerializer
            if fields in ["ship_from", "ship_to"]:
                serializer = AddressSerializer(data, context={"request": request})
            elif fields == "package":
                serializer = PackageSerializer(data, context={"request": request})
            return Response(serializer.data)
        else:
            serializer = self.get_serializer(shipment, context={"request": request})
            return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="assign-service")
    def assign_service(self, request, pk=None):
        service = request.data.get("shipping_service")
        if not service:
            return Response({"detail": "shipping_service is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            result = assign_shipping_service(int(pk), service)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        shipment = Shipment.objects.select_related("upload_session", "ship_from", "ship_to", "package").get(pk=pk)
        serializer = self.get_serializer(shipment, context={"request": request})
        summary = upload_session_summary(shipment.upload_session.id)
        return Response({"shipment": serializer.data, "assign_result": result, "upload_session_summary": summary})

    @action(detail=False, methods=["post"], url_path="bulk/update-service")
    def bulk_update_service(self, request):
        ser = BulkUpdateServiceSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = update_shipping_service(ser.validated_data["shipment_ids"], ser.validated_data["shipping_service"])
        return Response(result)

    @action(detail=False, methods=["post"], url_path="bulk/update-ship-from")
    def bulk_update_ship_from(self, request):
        ser = BulkUpdateShipFromSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = update_ship_from(ser.validated_data["shipment_ids"], ser.validated_data["address"])
        return Response(result)

    @action(detail=False, methods=["post"], url_path="bulk/update-package")
    def bulk_update_package(self, request):
        ser = BulkUpdatePackageSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = update_package(ser.validated_data["shipment_ids"], ser.validated_data["package"])
        return Response(result)

    @action(detail=False, methods=["post"], url_path="bulk/delete")
    def bulk_delete(self, request):
        ser = BulkDeleteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = delete_shipments(ser.validated_data["shipment_ids"])
        return Response(result)

    @action(detail=False, methods=["post", "delete"], url_path="delete-shipment")
    def delete_shipment(self, request):
        shipment_id = request.data.get("shipment_id") or request.query_params.get("shipment_id")
        if not shipment_id:
            return Response({"detail": "shipment_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            shipment = Shipment.objects.get(id=shipment_id)
            shipment.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Shipment.DoesNotExist:
            return Response({"detail": "Shipment not found"}, status=status.HTTP_404_NOT_FOUND)


class UploadSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only UploadSession endpoints plus:
    - upload (create via CSV) -> POST /uploads/upload/
    - shipments -> GET /uploads/{pk}/shipments/
    - summary -> GET /uploads/{pk}/summary/
    - checkout -> POST /uploads/{pk}/checkout/
    """
    queryset = UploadSession.objects.all()
    serializer_class = UploadSessionSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    lookup_field = "pk"

    @action(detail=False, methods=["post"], url_path="upload")
    def upload(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response(
                {
                    "error": "file is required",
                    "detail": "Please send a file with key 'file' as multipart/form-data"
                }, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            summary = process_csv_upload(upload)
            return Response(summary, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {"error": f"Failed to process CSV: {str(e)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["get"], url_path="shipments")
    def shipments(self, request, pk=None):
        qs = Shipment.objects.filter(upload_session__id=pk).select_related("ship_from", "ship_to", "package").order_by("-created_at")
        serializer = ShipmentReadSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="summary")
    def summary(self, request, pk=None):
        return Response(upload_session_summary(pk))

    @action(detail=True, methods=["post"], url_path="checkout")
    def checkout(self, request, pk=None):
        label_format = request.data.get("label_format", "pdf")
        try:
            result = process_checkout(pk, label_format)
        except ValueError as exc:
            payload = exc.args[0]
            if isinstance(payload, dict):
                return Response(payload, status=status.HTTP_400_BAD_REQUEST)
            return Response({"detail": str(payload)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)


class SavedAddressViewSet(viewsets.ModelViewSet):
    queryset = SavedAddress.objects.select_related("address").all()
    serializer_class = SavedAddressSerializer

    def create(self, request, *args, **kwargs):
        # Intercept creation to ensure the referenced Address is verified
        address_id = request.data.get('address_id')
        if address_id:
            try:
                from ..services.address_verification import AddressVerificationService
                from ..models import Address

                addr = Address.objects.get(pk=address_id)
                if not addr.is_verified:
                    avs = AddressVerificationService()
                    try:
                        res = avs.verify_address({
                            'name': addr.name,
                            'address_line1': addr.address_line1,
                            'address_line2': addr.address_line2,
                            'city': addr.city,
                            'state': addr.state,
                            'postal_code': addr.postal_code,
                            'phone': addr.phone,
                        }, country_code=None)
                    except Exception:
                        res = {'ok': False}
                    if res.get('ok'):
                        addr.is_verified = True
                        addr.verification_provider = res.get('provider') or ''
                        addr.verified_at = res.get('verified_at')
                        addr.verification_metadata = res.get('metadata') or {}
                        addr.save()
            except Exception:
                # Be permissive: don't fail SavedAddress creation if verification service errors
                pass
        return super().create(request, *args, **kwargs)


class SavedPackageViewSet(viewsets.ModelViewSet):
    queryset = SavedPackage.objects.select_related("package").all()
    serializer_class = SavedPackageSerializer