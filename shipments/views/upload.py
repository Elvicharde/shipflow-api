from __future__ import annotations
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from ..services.upload import process_csv_upload, format_address, format_package
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
            return Response({'detail': 'file is required'}, status=status.HTTP_400_BAD_REQUEST)

        summary = process_csv_upload(upload)
        return Response(summary, status=status.HTTP_201_CREATED)


class UploadSessionDetailView(APIView):
    """
    GET /api/shipments/uploads/upload-session/<uuid:upload_session_id>/
    Returns UploadResponse for the given session.
    """
    def get(self, request, upload_session_id):
        try:
            session = UploadSession.objects.get(id=upload_session_id)
        except UploadSession.DoesNotExist:
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

        response = {
            'upload_session_id': str(session.id),
            'total_rows': session.rows_total or len(results),
            'created': created,
            'invalid': invalid,
            'results': results,
            'errors': errors,
        }
        return Response(response, status=status.HTTP_200_OK)
