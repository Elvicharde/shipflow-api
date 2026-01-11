from __future__ import annotations
from typing import Dict, Any, List

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from ..models.upload_session import UploadSession, UploadSessionStatus
from ..models.shipment import Shipment, ShipmentStatus
from .validation import shipment_ready
from .session import upload_session_summary


ALLOWED_LABEL_FORMATS = {"pdf", "png"}


def process_checkout(upload_session_id, label_format: str) -> Dict[str, Any]:
    """
    Simulated checkout:
    - Validates each shipment in UploadSession for readiness.
    - Ensures shipping_service and price_cents are present.
    - Marks UploadSession.status and Shipments.status as PURCHASED.
    - Returns a confirmation summary with simulated label URLs.
    """
    label_format = (label_format or "").strip().lower()
    if label_format not in ALLOWED_LABEL_FORMATS:
        raise ValueError(f"unsupported label format: {label_format}")

    try:
        session = UploadSession.objects.get(pk=upload_session_id)
    except ObjectDoesNotExist:
        raise ValueError("upload session not found")

    shipments = list(Shipment.objects.filter(upload_session=session).select_related("ship_from", "ship_to", "package"))

    errors: List[Dict[str, Any]] = []
    for s in shipments:
        ready, validation_errors = shipment_ready(s)
        row_errors = {}
        if not ready:
            row_errors["validation"] = validation_errors
        # shipping_service and price must be present before purchase
        if not s.shipping_service:
            row_errors.setdefault("shipping_service", []).append("shipping_service is required")
        if s.price_cents is None:
            row_errors.setdefault("price_cents", []).append("price_cents is required")
        if row_errors:
            errors.append({"shipment_id": s.pk, "errors": row_errors})

    if errors:
        # return aggregated errors to caller
        raise ValueError({"errors": errors})

    # All good: persist purchase state
    with transaction.atomic():
        session.status = UploadSessionStatus.PURCHASED
        session.save(update_fields=["status"])

        purchased_ids: List[int] = []
        for s in shipments:
            s.status = ShipmentStatus.PURCHASED
            s.save(update_fields=["status", "updated_at"])
            purchased_ids.append(s.pk)

    summary = upload_session_summary(session.id)
    # Simulate label URLs
    labels = [{"shipment_id": sid, "label_url": f"/labels/{sid}.{label_format}"} for sid in purchased_ids]

    return {
        "upload_session_id": str(session.id),
        "label_format": label_format,
        "num_shipments": summary["num_shipments"],
        "num_purchased": len(purchased_ids),
        "total_price_cents": summary["total_price_cents"],
        "labels": labels,
    }