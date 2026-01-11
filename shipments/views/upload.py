from __future__ import annotations
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from ..services.upload import process_csv_upload


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