from __future__ import annotations
from io import StringIO
from typing import Any, Dict, List

from django.db import transaction

from ..models.upload_session import UploadSession, UploadSessionStatus
from ..models.shipment import Shipment, ShipmentStatus, ValidationStatus, PricingStatus
from ..models.address import Address
from ..models.package import Package
from .validation import validate_row
from .csv_parser import parse_csv


def process_csv_upload(file_like) -> Dict[str, Any]:
    """
    Parse CSV, validate each row, assign validation status, and persist results.
    Upload phase rules (Shipflow lifecycle):
      - Do NOT price shipments during upload
      - Do NOT require / enforce shipping_service during upload
      - Create Shipment records for BOTH valid and invalid rows
      - Since the Shipment model requires FK fields (ship_from, ship_to, package),
        we must create the related Address and Package records at upload time.
      - Store validation errors on the Shipment; pricing is deferred.

    Returns a summary payload for the frontend wizard with the original shape.
    """
    # Normalize input into a text-mode file-like object
    if hasattr(file_like, "read"):
        content = file_like.read()
        if isinstance(content, (bytes, bytearray)):
            content = content.decode("utf-8")
        file_obj = StringIO(content)
    else:
        file_obj = file_like

    # Create a new upload session
    session = UploadSession.objects.create(status=UploadSessionStatus.UPLOADED)

    # Parse rows from CSV (parse_csv is expected to skip fully empty rows already)
    rows = parse_csv(file_obj)
    total = len(rows)

    created = 0   # number of VALID rows
    invalid = 0   # number of INVALID rows
    errors: List[Dict[str, Any]] = []
    results: List[Dict[str, Any]] = []

    for idx, row in enumerate(rows, start=1):
        # Double-guard: skip fully empty rows (in case parse_csv didn't)
        if not any(row.values()):
            continue

        # Validate the row using provided validator; collect grouped field errors
        valid, field_errors = validate_row(row)
        validation_status = ValidationStatus.VALID if valid else ValidationStatus.INVALID

        # Upload phase: pricing deferred
        price = None
        currency = "USD"  # keep payload shape consistent

        # Attempt to persist this row independently so one failure doesn't abort the batch
        try:
            with transaction.atomic():
                # Build related objects required by the Shipment model (FKs are mandatory)
                ship_from_obj = Address.objects.create(**(row.get('data').get("ship_from") or {}))
                ship_to_obj = Address.objects.create(**(row.get('data').get("ship_to") or {}))
                package_obj = Package.objects.create(**(row.get('data').get("package") or {}))

                shipment = Shipment.objects.create(
                    upload_session=session,
                    ship_from=ship_from_obj,
                    ship_to=ship_to_obj,
                    package=package_obj,
                    # shipping_service is optional at upload; store if present, else None
                    shipping_service=row.get("shipping_service"),
                    price_cents=None,  # not computed during upload
                    status=ShipmentStatus.CREATED,
                    validation_status=validation_status,
                    validation_errors=field_errors or {},
                    pricing_status=PricingStatus.UNPRICED,
                )

            # Tally counts & per-row result
            if validation_status == ValidationStatus.VALID:
                created += 1
            else:
                invalid += 1
                errors.append({"row": idx, "errors": field_errors or {}})

            results.append({
                "row": idx,
                "shipment_id": shipment.id,
                "status": validation_status,
                "errors": field_errors or {},
                "price": price,
                "currency": currency,
            })

        except Exception as exc:
            # If we cannot persist this particular row (e.g., model constraints), record the error
            invalid += 1
            persist_errors = {"persist": [str(exc)]}
            errors.append({"row": idx, "errors": persist_errors})
            results.append({
                "row": idx,
                "shipment_id": None,
                "status": ValidationStatus.INVALID,
                "errors": persist_errors,
                "price": None,
                "currency": currency,
            })

    # Update session aggregates & status
    session.rows_total = total
    session.rows_valid = created
    session.rows_invalid = invalid
    # Session status: all valid -> VALIDATED; any invalid -> PARTIAL_VALID
    session.status = (
        UploadSessionStatus.VALIDATED if created > 0 and invalid == 0 
        else UploadSessionStatus.PARTIAL_VALID if created > 0 and invalid > 0 
        else UploadSessionStatus.INVALID
    )
    session.save()

    # Return summary payload (unchanged contract)
    return {
        "upload_session_id": str(session.id),
        "total_rows": total,
        "created": created,
        "invalid": invalid,
        "results": results,
        "errors": errors,
    }
