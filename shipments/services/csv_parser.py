from __future__ import annotations
import csv
from decimal import Decimal, InvalidOperation
from io import StringIO
from typing import Iterable, List, Dict, Any, Tuple

from rest_framework.exceptions import ValidationError

from ..serializers import AddressSerializer, PackageSerializer


from ..lib.constants import CSV_COLUMN_MAP
from core.logger import get_logger

logger = get_logger()



def _to_decimal(value: str):
    if value is None or value == '':
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def _to_int(value: str):
    if value is None or value == '':
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def _row_to_record(row: List[str]) -> Dict[str, Any]:
    # Ensure row has at least 23 entries
    row_extended = list(row) + [''] * max(0, 23 - len(row))
    mapped = {CSV_COLUMN_MAP[i]: row_extended[i].strip() for i in range(23)}
    # Normalize numeric types
    mapped['length_in'] = _to_decimal(mapped['length_in'])
    mapped['width_in'] = _to_decimal(mapped['width_in'])
    mapped['height_in'] = _to_decimal(mapped['height_in'])
    mapped['weight_lbs'] = _to_int(mapped['weight_lbs']) or 0
    mapped['weight_oz'] = _to_int(mapped['weight_oz']) or 0
    return mapped


def parse_csv(file_like: Iterable[str]) -> List[Dict[str, Any]]:
    """
    Parse CSV input (file-like iterable of lines or file object).
    - Skips first two header rows.
    - Maps columns 0..22 according to CSV_COLUMN_MAP.
    - Validates required fields using AddressSerializer and PackageSerializer.
    - Returns list of dicts:
      {
        'row': <1-based csv row index after skipping headers>,
        'raw': <original row list>,
        'data': {
            'ship_from': {...},
            'ship_to': {...},
            'package': {...},
            'shipping_service': ...,
            'price_cents': ...,
            'order_number': ...,
        },
        'errors': {
            'ship_from': {...} | None,
            'ship_to': {...} | None,
            'package': {...} | None,
            'row': {...}  # parsing/field-level errors
        }
      }
    """
    # Accept strings, file-like or iterables of lines
    request_id = None
    user_id = None
    operation = "csv_parse"
    entity = "csv_file"
    if hasattr(file_like, 'read'):
        content = file_like.read()
        file_like = StringIO(content)

    reader = csv.reader(file_like)
    # Skip two header rows
    try:
        next(reader)
        next(reader)
    except StopIteration:
        logger.warning(
            "CSV file missing headers or empty",
            extra={
                "operation": operation,
                "entity": entity,
                "status": "failure",
                "error_code": "missing_headers",
                "request_id": request_id,
                "user_id": user_id,
            },
        )
        return []

    results: List[Dict[str, Any]] = []
    for idx, row in enumerate(reader, start=1):
        try:
            record = _row_to_record(row)
        except Exception as exc:
            logger.error(
                "Malformed CSV row",
                extra={
                    "operation": operation,
                    "entity": "csv_row",
                    "row_number": idx,
                    "status": "failure",
                    "error_code": "malformed_row",
                    "error_message": str(exc),
                    "request_id": request_id,
                    "user_id": user_id,
                },
            )
            continue
        ship_from = {
            'name': f"{record['ship_from_first_name']} {record['ship_from_last_name']}",
            'address_line1': record['ship_from_address_line1'],
            'address_line2': record['ship_from_address_line2'],
            'city': record['ship_from_city'],
            'state': record['ship_from_state'],
            'postal_code': record['ship_from_postal_code'],
            'phone': None,
        }
        ship_to = {
            'name': f"{record['ship_from_first_name']} {record['ship_from_last_name']}",
            'address_line1': record['ship_to_address_line1'],
            'address_line2': record['ship_to_address_line2'],
            'city': record['ship_to_city'],
            'state': record['ship_to_state'],
            'postal_code': record['ship_to_postal_code'],
            'phone': f"{record['ship_to_phone1']}{', ' + record['ship_to_phone2'].strip() if len(record['ship_to_phone2'].strip()) > 0 else ''}",
        }
        package = {
            'sku': record['sku'],
            'length_in': record['length_in'],
            'width_in': record['width_in'],
            'height_in': record['height_in'],
            'weight_lbs': record['weight_lbs'],
            'weight_oz': record['weight_oz'],
        }
        shipment_payload = {
            'ship_from': ship_from,
            'ship_to': ship_to,
            'package': package,
            'shipping_service': None,
            'price_cents': None,
            'order_number': record['order_number'],
        }
        results.append({
            'row': idx,
            'raw': row,
            'data': shipment_payload,
        })
    logger.info(
        "CSV parsing complete",
        extra={
            "operation": operation,
            "entity": entity,
            "status": "success",
            "row_count": len(results),
            "request_id": request_id,
            "user_id": user_id,
        },
    )
    return results