from __future__ import annotations
from typing import Dict

from django.db.models import Sum, Count, Q
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from ..services.bulk_ops import assign_shipping_service
from ..services.session import upload_session_summary
from ..serializers import ShipmentSerializer

from ..models import Shipment


def upload_session_summary(upload_session_id) -> Dict[str, int]:
    """
    Return summary totals for an UploadSession:
      - total_price_cents: sum of price_cents (treat None as 0)
      - num_shipments: total shipments in session
      - num_priced: shipments with non-null price_cents
    """
    qs = Shipment.objects.filter(upload_session__id=upload_session_id)
    agg = qs.aggregate(
        total_price_cents=Sum('price_cents'),
        num_shipments=Count('pk'),
        num_priced=Count('pk', filter=~(Shipment.price_cents.__eq__(None))),  # type: ignore[misc]
    )
    # Sum can be None if no priced shipments; coerce to int
    total = agg.get('total_price_cents') or 0
    return {
        'upload_session_id': str(upload_session_id),
        'total_price_cents': int(total),
        'num_shipments': int(agg.get('num_shipments') or 0),
        'num_priced': int(agg.get('num_priced') or 0),
    }


class ShipmentListView(generics.ListAPIView):
    """
    List shipments for a given UploadSession.
    Supports simple `?q=` search against ship_from.name, ship_to.name, order_number, and shipping_service.
    """
    serializer_class = ShipmentSerializer

    def get_queryset(self):
        upload_session_id = self.kwargs.get("upload_session_id")
        qs = Shipment.objects.filter(upload_session__id=upload_session_id).select_related(
            "ship_from", "ship_to", "package"
        )
        q = self.request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(ship_from__name__icontains=q)
                | Q(ship_to__name__icontains=q)
                | Q(order_number__icontains=q)
                | Q(shipping_service__icontains=q)
            )
        return qs.order_by("-created_at")


class ShipmentDetailView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or partially update a single shipment.
    Nested partial updates are supported (see [`shipments.serializers.shipment.ShipmentSerializer`](shipments/serializers/shipment.py)).
    """
    queryset = Shipment.objects.select_related("ship_from", "ship_to", "package").all()
    serializer_class = ShipmentSerializer

    def patch(self, request, *args, **kwargs):
        # allow PATCH to behave as partial_update
        return self.partial_update(request, *args, **kwargs)


class ShipmentAssignServiceView(APIView):
    """
    POST /api/shipments/shipments/<pk>/assign-service/
    Body: { "shipping_service": "Priority" }
    Returns updated Shipment data and the upload session running total.
    """
    def post(self, request, pk):
        service = request.data.get('shipping_service')
        if not service:
            return Response({'detail': 'shipping_service is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            result = assign_shipping_service(pk, service)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        shipment = Shipment.objects.select_related('upload_session', 'ship_from', 'ship_to', 'package').get(pk=pk)
        serializer = ShipmentSerializer(shipment, context={'request': request})
        summary = upload_session_summary(shipment.upload_session.id)
        payload = {
            'shipment': serializer.data,
            'assign_result': result,
            'upload_session_summary': summary,
        }
        return Response(payload, status=status.HTTP_200_OK)


class UploadSessionSummaryView(APIView):
    """
    GET /api/shipments/uploads/<upload_session_id>/summary/
    Returns running totals for the upload session.
    """
    def get(self, request, upload_session_id):
        summary = upload_session_summary(upload_session_id)
        return Response(summary, status=status.HTTP_200_OK)