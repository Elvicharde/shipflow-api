from __future__ import annotations
from rest_framework.views import APIView
from rest_framework.response import Response

from ..serializers.bulk import (
    BulkUpdateShipFromSerializer,
    BulkUpdatePackageSerializer,
    BulkUpdateServiceSerializer,
    BulkDeleteSerializer,
)
from ..services.bulk_ops import (
    update_ship_from,
    update_package,
    update_shipping_service,
    delete_shipments,
)
from shipments.serializers.bulk_update_service_option import BulkUpdateServiceAndOptionSerializer
from shipments.services.bulk_ops import bulk_update_shipping_service_and_option

from shipments.serializers.shipment import ShipmentReadSerializer

class BulkUpdateShippingServiceAndOptionView(APIView):
    def post(self, request):
        serializer = BulkUpdateServiceAndOptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session_id = serializer.validated_data['upload_session_id']
        shipment_updates = serializer.validated_data['shipments']
        from shipments.models import UploadSession
        try:
            session = UploadSession.objects.get(pk=session_id)
        except UploadSession.DoesNotExist:
            return Response({'detail': 'Session not found'}, status=404)
        updated = bulk_update_shipping_service_and_option(session, shipment_updates)
        
        return Response(ShipmentReadSerializer(updated, many=True).data)



class BulkUpdateShipFromView(APIView):
    def post(self, request):
        serializer = BulkUpdateShipFromSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = update_ship_from(
            serializer.validated_data['shipment_ids'],
            serializer.validated_data['address']
        )
        return Response(result)


class BulkUpdatePackageView(APIView):
    def post(self, request):
        serializer = BulkUpdatePackageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = update_package(
            serializer.validated_data['shipment_ids'],
            serializer.validated_data['package']
        )
        return Response(result)


class BulkUpdateShippingServiceView(APIView):
    def post(self, request):
        serializer = BulkUpdateServiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = update_shipping_service(
            serializer.validated_data['shipment_ids'],
            serializer.validated_data['shipping_service']
        )
        return Response(result)


class BulkDeleteShipmentsView(APIView):
    def post(self, request):
        ser = BulkDeleteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = delete_shipments(ser.validated_data['shipment_ids'])
        return Response(result)