from __future__ import annotations
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from ..services.checkout import process_checkout


class CheckoutView(APIView):
    """
    POST /api/shipments/uploads/<upload_session_id>/checkout/
    Body: { "label_format": "pdf" }
    """
    def post(self, request, upload_session_id):
        label_format = request.data.get("label_format", "pdf")
        try:
            result = process_checkout(upload_session_id, label_format)
        except ValueError as exc:
            # exc may carry a dict of errors
            payload = exc.args[0]
            if isinstance(payload, dict):
                return Response(payload, status=status.HTTP_400_BAD_REQUEST)
            return Response({"detail": str(payload)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)