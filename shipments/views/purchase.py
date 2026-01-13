from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..services.purchase import purchase_upload_session

class PurchaseView(APIView):
    def post(self, request, upload_session_id):
        label_format = request.data.get('label_format', 'pdf')
        result = purchase_upload_session(upload_session_id, label_format)
        return Response(result, status=status.HTTP_200_OK)
