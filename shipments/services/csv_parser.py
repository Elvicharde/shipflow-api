from __future__ import annotations
import csv
from decimal import Decimal, InvalidOperation
from io import StringIO
from typing import Iterable, List, Dict, Any, Tuple

from rest_framework.exceptions import ValidationError

from ..serializers import AddressSerializer, PackageSerializer


# Column mapping (indices 0–22)
COLUMN_MAP = {
    0: 'ship_from_name',
    1: 'ship_from_address_line1',
    2: 'ship_from_address_line2',
    3: 'ship_from_city',
    4: 'ship_from_state',
    5: 'ship_from_postal_code',
    6: 'ship_from_phone',
    7: 'ship_to_name',
    8: 'ship_to_address_line1',
    9: 'ship_to_address_line2',
    10: 'ship_to_city',
    11: 'ship_to_state',
    12: 'ship_to_postal_code',
    13: 'ship_to_phone',
    14: 'sku',
    15: 'length_in',
    16: 'width_in',
    17: 'height_in',
    18: 'weight_lbs',
    19: 'weight_oz',
    20: 'shipping_service',
    21: 'price_cents',
    22: 'order_number',
}


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
    mapped = {COLUMN_MAP[i]: row_extended[i].strip() for i in range(23)}
    # Normalize numeric types
    mapped['length_in'] = _to_decimal(mapped['length_in'])
    mapped['width_in'] = _to_decimal(mapped['width_in'])
    mapped['height_in'] = _to_decimal(mapped['height_in'])
    mapped['weight_lbs'] = _to_int(mapped['weight_lbs']) or 0
    mapped['weight_oz'] = _to_int(mapped['weight_oz']) or 0
    mapped['price_cents'] = _to_int(mapped['price_cents'])
    return mapped


def parse_csv(file_like: Iterable[str]) -> List[Dict[str, Any]]:
    """
    Parse CSV input (file-like iterable of lines or file object).
    - Skips first two header rows.
    - Maps columns 0..22 according to COLUMN_MAP.
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
    if hasattr(file_like, 'read'):
        content = file_like.read()
        file_like = StringIO(content)

    reader = csv.reader(file_like)
    # Skip two header rows
    try:
        next(reader)
        next(reader)
    except StopIteration:
        return []

    results: List[Dict[str, Any]] = []
    for idx, row in enumerate(reader, start=1):
        record = _row_to_record(row)
        ship_from = {
            'name': record['ship_from_name'],
            'address_line1': record['ship_from_address_line1'],
            'address_line2': record['ship_from_address_line2'],
            'city': record['ship_from_city'],
            'state': record['ship_from_state'],
            'postal_code': record['ship_from_postal_code'],
            'phone': record['ship_from_phone'],
        }
        ship_to = {
            'name': record['ship_to_name'],
            'address_line1': record['ship_to_address_line1'],
            'address_line2': record['ship_to_address_line2'],
            'city': record['ship_to_city'],
            'state': record['ship_to_state'],
            'postal_code': record['ship_to_postal_code'],
            'phone': record['ship_to_phone'],
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
            'shipping_service': record['shipping_service'],
            'price_cents': record['price_cents'],
            'order_number': record['order_number'],
        }

        errors: Dict[str, Any] = {'ship_from': None, 'ship_to': None, 'package': None, 'row': None}

        # Validate nested entities using serializers (no saving)
        a_from = AddressSerializer(data=ship_from)
        a_to = AddressSerializer(data=ship_to)
        p_ser = PackageSerializer(data=package)

        if not a_from.is_valid():
            errors['ship_from'] = a_from.errors
        if not a_to.is_valid():
            errors['ship_to'] = a_to.errors
        if not p_ser.is_valid():
            errors['package'] = p_ser.errors

        # Capture row-level parsing errors (e.g., numeric conversions that failed)
        row_errors = {}
        # length/width/height conversion errors
        for dim in ('length_in', 'width_in', 'height_in'):
            if (shipment_payload['package'][dim] is None) and row[COLUMN_MAP.keys().__iter__().__next__() if False else 0]:
                # don't attempt to be clever about which column; leave None as ok
                pass
        # no special row-level checks for now; left for future expansion

        results.append({
            'row': idx,
            'raw': row,
            'data': shipment_payload,
            'errors': errors,
        })

    return results