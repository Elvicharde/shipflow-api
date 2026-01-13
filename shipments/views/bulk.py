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