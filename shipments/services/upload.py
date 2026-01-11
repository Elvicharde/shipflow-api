from __future__ import annotations
from io import StringIO
from typing import Any, Dict, List

from django.db import transaction

from ..models.upload_session import UploadSession
from .csv_parser import parse_csv
from ..serializers import ShipmentSerializer


def process_csv_upload(file_like) -> Dict[str, Any]:
    """
    Create an UploadSession, parse the uploaded CSV, persist valid shipments,
    and return a summary:
      {
        'upload_session_id': str(UUID),
        'total_rows': int,
        'created': int,
        'invalid': int,
        'errors': [{'row': int, 'errors': {...}}, ...]
      }

    - Accepts file-like or Django UploadedFile; decodes bytes if needed.
    - Uses parse_csv for mapping and initial validation ([shipments.services.csv_parser.parse_csv]).
    - Uses ShipmentSerializer to persist nested Address/Package/Shipment objects.
    """
    # Normalize uploaded file to text file-like for parser
    if hasattr(file_like, 'read'):
        content = file_like.read()
        if isinstance(content, (bytes, bytearray)):
            content = content.decode('utf-8')
        file_obj = StringIO(content)
    else:
        file_obj = file_like

    session = UploadSession.objects.create()

    rows = parse_csv(file_obj)
    total = len(rows)
    created = 0
    errors: List[Dict[str, Any]] = []

    for row in rows:
        row_idx = row.get('row')
        parse_errors = row.get('errors') or {}
        # If parse step reported any nested errors, skip persistence
        if any(parse_errors.get(k) for k in ('ship_from', 'ship_to', 'package')):
            errors.append({'row': row_idx, 'errors': parse_errors})
            continue

        payload = dict(row['data'])
        payload['upload_session'] = session.pk

        # Run address verification for ship_from and ship_to (non-blocking)
        try:
            from .address_verification import AddressVerificationService
            avs = AddressVerificationService()
            for addr_key in ('ship_from', 'ship_to'):
                addr_data = payload.get(addr_key, {})
                try:
                    result = avs.verify_address(addr_data, country_code=None)
                except Exception as e:
                    result = {'ok': False, 'error': str(e)}
                if result.get('ok'):
                    addr_data['is_verified'] = True
                    addr_data['verification_provider'] = result.get('provider')
                    # datetime to ISO string
                    if result.get('verified_at'):
                        addr_data['verified_at'] = result.get('verified_at').isoformat()
                    addr_data['verification_metadata'] = result.get('metadata') or {}
                else:
                    addr_data['is_verified'] = False
                    addr_data.setdefault('verification_metadata', {})
                payload[addr_key] = addr_data
        except ImportError:
            # verification service not available; continue without verifying
            pass

        serializer = ShipmentSerializer(data=payload)
        if not serializer.is_valid():
            errors.append({'row': row_idx, 'errors': serializer.errors})
            continue

        # Persist nested objects/shipment in a per-row transaction
        try:
            with transaction.atomic():
                serializer.save()
            created += 1
        except Exception as exc:  # pragma: no cover - defensive
            errors.append({'row': row_idx, 'errors': {'exception': [str(exc)]}})

    return {
        'upload_session_id': str(session.id),
        'total_rows': total,
        'created': created,
        'invalid': len(errors),
        'errors': errors,
    }