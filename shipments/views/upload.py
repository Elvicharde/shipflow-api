
from __future__ import annotations
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from ..services.upload import process_csv_upload, format_address, format_package
from core.logger import get_logger

logger = get_logger()
from shipments.models.upload_session import UploadSession
from shipments.models.shipment import Shipment

## Removed local format_address and format_package; now imported from services.upload



class UploadCSVView(APIView):
    """
    POST /api/shipments/upload/
    Expects multipart form with 'file' key (CSV). Returns upload summary.
    """
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        upload = request.FILES.get('file') or request.data.get('file')
        if not upload:
            logger.warning(
                "CSV upload request missing file",
                extra={
                    "operation": "csv_upload",
                    "entity": "csv_file",
                    "status": "failure",
                    "request_id": request.headers.get('X-Request-Id'),
                    "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
                },
            )
            return Response({'detail': 'file is required'}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(
            "CSV upload API called",
            extra={
                "operation": "csv_upload",
                "entity": "csv_file",
                "status": "start",
                "request_id": request.headers.get('X-Request-Id'),
                "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            },
        )
        try:
            summary = process_csv_upload(upload)
            logger.info(
                "CSV upload API completed",
                extra={
                    "operation": "csv_upload",
                    "entity": "csv_file",
                    "status": "success",
                    "request_id": request.headers.get('X-Request-Id'),
                    "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
                },
            )
            return Response(summary, status=status.HTTP_201_CREATED)
        except Exception as exc:
            logger.error(
                "CSV upload API failed",
                extra={
                    "operation": "csv_upload",
                    "entity": "csv_file",
                    "status": "failure",
                    "error_code": "upload_exception",
                    "error_message": str(exc),
                    "request_id": request.headers.get('X-Request-Id'),
                    "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
                },
            )
            raise


class UploadSessionDetailView(APIView):
    """
    GET /api/shipments/uploads/upload-session/<uuid:upload_session_id>/
    Returns UploadResponse for the given session.
    """
    def get(self, request, upload_session_id):
        try:
            session = UploadSession.objects.get(id=upload_session_id)
        except UploadSession.DoesNotExist:
            logger.warning(
                "UploadSession not found",
                extra={
                    "operation": "get_upload_session",
                    "entity": "upload_session",
                    "status": "failure",
                    "upload_session_id": upload_session_id,
                    "request_id": request.headers.get('X-Request-Id'),
                    "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
                },
            )
            return Response({'detail': 'UploadSession not found'}, status=status.HTTP_404_NOT_FOUND)

        shipments = Shipment.objects.filter(upload_session=session).order_by('row_number')
        results = []
        errors = []
        created = 0
        invalid = 0
        for shipment in shipments:
            result = {
                'row': shipment.row_number,
                'shipment_id': shipment.id,
                'status': shipment.validation_status,
                'errors': shipment.validation_errors or {},
                'price': shipment.price_cents,
                'currency': 'USD',
                'ship_from_address': format_address(shipment.ship_from),
                'ship_to_address': format_address(shipment.ship_to),
                'package_details': format_package(shipment.package),
                'order_number': getattr(shipment, 'order_number', None),
            }
            results.append(result)
            if shipment.validation_status == 'valid':
                created += 1
            else:
                invalid += 1
                errors.append({'shipment_id': shipment.id, 'errors': shipment.validation_errors or {}})

        logger.info(
            "UploadSession detail fetched",
            extra={
                "operation": "get_upload_session",
                "entity": "upload_session",
                "status": "success",
                "upload_session_id": upload_session_id,
                "row_count": len(results),
                "request_id": request.headers.get('X-Request-Id'),
                "user_id": getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            },
        )
        response = {
            'upload_session_id': str(session.id),
            'total_rows': session.rows_total or len(results),
            'created': created,
            'invalid': invalid,
            'results': results,
            'errors': errors,
        }
        return Response(response, status=status.HTTP_200_OK)
