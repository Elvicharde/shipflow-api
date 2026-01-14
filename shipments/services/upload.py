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
from core.logger import get_logger

logger = get_logger()

def format_address(addr: Address | None) -> str:
    if not addr:
        return None
    parts = [
        addr.address_line1,
        addr.address_line2,
        addr.city,
        addr.state,
        addr.postal_code,
    ]
    return ', '.join([str(p) for p in parts if p]).rstrip(',').strip()

def format_package(pkg: Package | None) -> dict:
    if not pkg:
        return None
    return {
        "length_in": pkg.length_in,
        "width_in": pkg.width_in,
        "height_in": pkg.height_in,
        "weight_lbs": pkg.weight_lbs,
        "weight_oz": pkg.weight_oz,
    }



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

    request_id = None  # Optionally extract from context/middleware if available
    user_id = None     # Optionally extract from context/middleware if available
    operation = "csv_upload"
    entity = "csv_file"
    status = "start"
    logger.info(
        "CSV upload started",
        extra={
            "operation": operation,
            "entity": entity,
            "status": status,
            "request_id": request_id,
            "user_id": user_id,
        },
    )

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


    # Parse rows from CSV
    try:
        rows = parse_csv(file_obj)
        total = len(rows)
        logger.info(
            "CSV parsed",
            extra={
                "operation": operation,
                "entity": entity,
                "status": "parsed",
                "row_count": total,
                "request_id": request_id,
                "user_id": user_id,
            },
        )
    except Exception as exc:
        logger.error(
            "CSV parsing failed",
            extra={
                "operation": operation,
                "entity": entity,
                "status": "failure",
                "error_code": "csv_parse_error",
                "error_message": str(exc),
                "request_id": request_id,
                "user_id": user_id,
            },
        )
        raise

    created = 0   # number of VALID rows
    invalid = 0   # number of INVALID rows
    errors: List[Dict[str, Any]] = []
    results: List[Dict[str, Any]] = []


    for idx, row in enumerate(rows, start=1):
        if not any(row.values()):
            continue

        # Validate the row
        valid, field_errors = validate_row(row)
        validation_status = ValidationStatus.VALID if valid else ValidationStatus.INVALID
        price = None
        currency = "USD"
        entity = "csv_row"
        try:
            with transaction.atomic():
                ship_from_obj = Address.objects.create(**(row.get('data').get("ship_from") or {}))
                ship_to_obj = Address.objects.create(**(row.get('data').get("ship_to") or {}))
                package_obj = Package.objects.create(**(row.get('data').get("package") or {}))
                shipment = Shipment.objects.create(
                    upload_session=session,
                    ship_from=ship_from_obj,
                    ship_to=ship_to_obj,
                    package=package_obj,
                    shipping_service=row.get("shipping_service"),
                    price_cents=None,
                    status=ShipmentStatus.CREATED,
                    validation_status=validation_status,
                    validation_errors=field_errors or {},
                    pricing_status=PricingStatus.UNPRICED,
                    row_number=idx,
                )
            logger.info(
                "Row processed",
                extra={
                    "operation": operation,
                    "entity": entity,
                    "row_number": idx,
                    "status": "success" if valid else "invalid",
                    "request_id": request_id,
                    "user_id": user_id,
                    "validation_errors": field_errors if not valid else None,
                },
            )
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
                "ship_from_address": format_address(ship_from_obj),
                "ship_to_address": format_address(ship_to_obj),
                "package_details": format_package(package_obj),
                "order_number": getattr(shipment, "order_number", None),
            })
        except Exception as exc:
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
                "ship_from_address": None,
                "ship_to_address": None,
                "package_details": None,
                "order_number": None,
            })
            logger.error(
                "Row persistence failed",
                extra={
                    "operation": operation,
                    "entity": entity,
                    "row_number": idx,
                    "status": "failure",
                    "error_code": "row_persist_error",
                    "error_message": str(exc),
                    "request_id": request_id,
                    "user_id": user_id,
                },
            )


    # Update session aggregates & status
    session.rows_total = total
    session.rows_valid = created
    session.rows_invalid = invalid
    session.status = (
        UploadSessionStatus.VALIDATED if created > 0 and invalid == 0
        else UploadSessionStatus.PARTIAL_VALID if created > 0 and invalid > 0
        else UploadSessionStatus.INVALID
    )
    session.save()

    logger.info(
        "CSV upload completed",
        extra={
            "operation": operation,
            "entity": "csv_file",
            "status": "success" if created > 0 and invalid == 0 else ("partial" if created > 0 else "failure"),
            "row_count": total,
            "valid_rows": created,
            "invalid_rows": invalid,
            "request_id": request_id,
            "user_id": user_id,
        },
    )

    return {
        "upload_session_id": str(session.id),
        "total_rows": total,
        "created": created,
        "invalid": invalid,
        "results": results,
        "errors": errors,
    }
