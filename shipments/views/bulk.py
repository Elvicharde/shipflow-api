from __future__ import annotations
from core.logger import get_logger

logger = get_logger()
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
from rest_framework.permissions import IsAuthenticated

class BulkUpdateShippingServiceAndOptionView(APIView):
    authentication_classes = []
    permission_classes = [IsAuthenticated]
    def post(self, request):
        serializer = BulkUpdateServiceAndOptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session_id = serializer.validated_data['upload_session_id']
        shipment_updates = serializer.validated_data['shipments']
        from shipments.models import UploadSession
        try:
            session = UploadSession.objects.get(pk=session_id)
        except UploadSession.DoesNotExist:
            logger.warning(
                "Bulk update service/option: session not found",
                extra={
                    "operation": "bulk_update_shipping_service_and_option",
                    "entity": "upload_session",
                    "status": "failure",
                    "upload_session_id": session_id,
                    "request_id": request.headers.get('X-Request-Id'),
                    "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
                },
            )
            return Response({'detail': 'Session not found'}, status=404)
        logger.info(
            "Bulk update shipping service/option API called",
            extra={
                "operation": "bulk_update_shipping_service_and_option",
                "entity": "shipment",
                "status": "start",
                "count": len(shipment_updates),
                "upload_session_id": session_id,
                "request_id": request.headers.get('X-Request-Id'),
                "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            },
        )
        try:
            updated = bulk_update_shipping_service_and_option(session, shipment_updates)
            logger.info(
                "Bulk update shipping service/option API completed",
                extra={
                    "operation": "bulk_update_shipping_service_and_option",
                    "entity": "shipment",
                    "status": "success",
                    "updated_count": len(updated),
                    "upload_session_id": session_id,
                    "request_id": request.headers.get('X-Request-Id'),
                    "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
                },
            )
            return Response(ShipmentReadSerializer(updated, many=True).data)
        except Exception as exc:
            logger.error(
                "Bulk update shipping service/option API failed",
                extra={
                    "operation": "bulk_update_shipping_service_and_option",
                    "entity": "shipment",
                    "status": "failure",
                    "error_code": "bulk_update_exception",
                    "error_message": str(exc),
                    "upload_session_id": session_id,
                    "request_id": request.headers.get('X-Request-Id'),
                    "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
                },
            )
            raise



class BulkUpdateShipFromView(APIView):
    def post(self, request):
        serializer = BulkUpdateShipFromSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        logger.info(
            "Bulk update ship_from API called",
            extra={
                "operation": "bulk_update_ship_from",
                "entity": "shipment",
                "status": "start",
                "count": len(serializer.validated_data['shipment_ids']),
                "request_id": request.headers.get('X-Request-Id'),
                "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            },
        )
        try:
            result = update_ship_from(
                serializer.validated_data['shipment_ids'],
                serializer.validated_data['address']
            )
            logger.info(
                "Bulk update ship_from API completed",
                extra={
                    "operation": "bulk_update_ship_from",
                    "entity": "shipment",
                    "status": "success",
                    "updated_count": len(result.get('updated', [])),
                    "failed_count": len(result.get('errors', {})),
                    "request_id": request.headers.get('X-Request-Id'),
                    "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
                },
            )
            return Response(result)
        except Exception as exc:
            logger.error(
                "Bulk update ship_from API failed",
                extra={
                    "operation": "bulk_update_ship_from",
                    "entity": "shipment",
                    "status": "failure",
                    "error_code": "bulk_update_shipfrom_exception",
                    "error_message": str(exc),
                    "request_id": request.headers.get('X-Request-Id'),
                    "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
                },
            )
            raise


class BulkUpdatePackageView(APIView):
    def post(self, request):
        serializer = BulkUpdatePackageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        logger.info(
            "Bulk update package API called",
            extra={
                "operation": "bulk_update_package",
                "entity": "shipment",
                "status": "start",
                "count": len(serializer.validated_data['shipment_ids']),
                "request_id": request.headers.get('X-Request-Id'),
                "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            },
        )
        try:
            result = update_package(
                serializer.validated_data['shipment_ids'],
                serializer.validated_data['package']
            )
            logger.info(
                "Bulk update package API completed",
                extra={
                    "operation": "bulk_update_package",
                    "entity": "shipment",
                    "status": "success",
                    "updated_count": len(result.get('updated', [])),
                    "failed_count": len(result.get('errors', {})),
                    "request_id": request.headers.get('X-Request-Id'),
                    "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
                },
            )
            return Response(result)
        except Exception as exc:
            logger.error(
                "Bulk update package API failed",
                extra={
                    "operation": "bulk_update_package",
                    "entity": "shipment",
                    "status": "failure",
                    "error_code": "bulk_update_package_exception",
                    "error_message": str(exc),
                    "request_id": request.headers.get('X-Request-Id'),
                    "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
                },
            )
            raise


class BulkUpdateShippingServiceView(APIView):
    def post(self, request):
        serializer = BulkUpdateServiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        logger.info(
            "Bulk update shipping_service API called",
            extra={
                "operation": "bulk_update_shipping_service",
                "entity": "shipment",
                "status": "start",
                "count": len(serializer.validated_data['shipment_ids']),
                "request_id": request.headers.get('X-Request-Id'),
                "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            },
        )
        try:
            result = update_shipping_service(
                serializer.validated_data['shipment_ids'],
                serializer.validated_data['shipping_service']
            )
            logger.info(
                "Bulk update shipping_service API completed",
                extra={
                    "operation": "bulk_update_shipping_service",
                    "entity": "shipment",
                    "status": "success",
                    "updated_count": len(result.get('updated', [])),
                    "failed_count": len(result.get('errors', {})),
                    "request_id": request.headers.get('X-Request-Id'),
                    "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
                },
            )
            return Response(result)
        except Exception as exc:
            logger.error(
                "Bulk update shipping_service API failed",
                extra={
                    "operation": "bulk_update_shipping_service",
                    "entity": "shipment",
                    "status": "failure",
                    "error_code": "bulk_update_shipping_service_exception",
                    "error_message": str(exc),
                    "request_id": request.headers.get('X-Request-Id'),
                    "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
                },
            )
            raise


class BulkDeleteShipmentsView(APIView):
    def post(self, request):
        ser = BulkDeleteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        logger.info(
            "Bulk delete shipments API called",
            extra={
                "operation": "bulk_delete_shipments",
                "entity": "shipment",
                "status": "start",
                "count": len(ser.validated_data['shipment_ids']),
                "request_id": request.headers.get('X-Request-Id'),
                "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            },
        )
        try:
            result = delete_shipments(ser.validated_data['shipment_ids'])
            logger.info(
                "Bulk delete shipments API completed",
                extra={
                    "operation": "bulk_delete_shipments",
                    "entity": "shipment",
                    "status": "success",
                    "deleted_count": len(result.get('deleted', [])),
                    "not_found_count": len(result.get('not_found', [])),
                    "request_id": request.headers.get('X-Request-Id'),
                    "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
                },
            )
            return Response(result)
        except Exception as exc:
            logger.error(
                "Bulk delete shipments API failed",
                extra={
                    "operation": "bulk_delete_shipments",
                    "entity": "shipment",
                    "status": "failure",
                    "error_code": "bulk_delete_shipments_exception",
                    "error_message": str(exc),
                    "request_id": request.headers.get('X-Request-Id'),
                    "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
                },
            )
            raise