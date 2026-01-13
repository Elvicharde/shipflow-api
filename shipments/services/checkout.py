from __future__ import annotations
from typing import Dict, Any, List

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from ..models.upload_session import UploadSession, UploadSessionStatus
from ..models.shipment import Shipment, ShipmentStatus, ValidationStatus, PricingStatus
from .validation import shipment_ready
from .session import upload_session_summary


ALLOWED_LABEL_FORMATS = {"pdf", "png"}


def process_checkout(upload_session_id: int, label_format: str) -> Dict[str, Any]:

    """
    Atomically purchase all VALID and PRICED shipments in session.
    Enforces idempotency and locks shipments.
    Returns label stubs and summary.
    """
    label_format = (label_format or "").strip().lower()
    if label_format not in ALLOWED_LABEL_FORMATS:
        raise ValueError(f"unsupported label format: {label_format}")

    try:
        session = UploadSession.objects.get(pk=upload_session_id)
    except ObjectDoesNotExist:
        raise ValueError("upload session not found")

    if session.status == UploadSessionStatus.PURCHASED:
        raise ValueError("Session already purchased")

    shipments = list(Shipment.objects.filter(upload_session=session).select_related("ship_from", "ship_to", "package"))

    errors: List[Dict[str, Any]] = []
    for s in shipments:
        if s.validation_status != ValidationStatus.VALID or s.pricing_status != PricingStatus.PRICED:
            errors.append({'shipment_id': s.id, 'errors': 'Shipment must be VALID and PRICED'})
        if s.locked:
            errors.append({'shipment_id': s.id, 'errors': 'Shipment is locked'})

    if errors:
        raise ValueError({'errors': errors})

    with transaction.atomic():
        session.status = UploadSessionStatus.PURCHASED
        session.save(update_fields=['status'])
        purchased_ids: List[int] = []
        for s in shipments:
            s.locked = True
            s.status = ShipmentStatus.PURCHASED
            s.save(update_fields=['locked', 'status', 'updated_at'])
            purchased_ids.append(s.pk)

    summary = upload_session_summary(session.id)
    labels = [{'shipment_id': sid, 'label_url': f'/labels/{sid}.{label_format}'} for sid in purchased_ids]

    return {
        'upload_session_id': str(session.id),
        'label_format': label_format,
        'num_shipments': summary['num_shipments'],
        'num_purchased': len(purchased_ids),
        'total_price_cents': summary['total_price_cents'],
        'labels': labels,
    }