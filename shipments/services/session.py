from __future__ import annotations
from typing import Dict

from django.db.models import Sum, Count

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