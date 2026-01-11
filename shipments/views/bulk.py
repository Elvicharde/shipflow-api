from __future__ import annotations
from rest_framework.views import APIView
from rest_framework.response import Response

from ..serializers.bulk import (
    BulkUpdateShipFromSerializer,
    BulkUpdatePackageSerializer,
    BulkUpdateServiceSerializer,
    BulkDeleteSerializer,
)
from ..services import (
    update_ship_from,
    update_package,
    update_shipping_service,
    delete_shipments,
)


class BulkUpdateShipFromView(APIView):
    def post(self, request):
        ser = BulkUpdateShipFromSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = update_ship_from(ser.validated_data['shipment_ids'], ser.validated_data['address'])
        return Response(result)


class BulkUpdatePackageView(APIView):
    def post(self, request):
        ser = BulkUpdatePackageSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = update_package(ser.validated_data['shipment_ids'], ser.validated_data['package'])
        return Response(result)


class BulkUpdateShippingServiceView(APIView):
    def post(self, request):
        ser = BulkUpdateServiceSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = update_shipping_service(ser.validated_data['shipment_ids'], ser.validated_data['shipping_service'])
        return Response(result)


class BulkDeleteShipmentsView(APIView):
    def post(self, request):
        ser = BulkDeleteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = delete_shipments(ser.validated_data['shipment_ids'])
        return Response(result)