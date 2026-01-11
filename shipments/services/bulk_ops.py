from __future__ import annotations
from typing import Dict, List, Any

from django.db import transaction

from ..models import Shipment
from ..serializers import AddressSerializer, PackageSerializer
from .pricing import calculate_price_for_package


def _fetch_shipments(ids: List[int]) -> List[Shipment]:
    return list(Shipment.objects.filter(pk__in=ids).select_related('ship_from', 'package'))


def update_ship_from(shipment_ids: List[int], address_data: Dict[str, Any]) -> Dict[str, Any]:
    shipments = _fetch_shipments(shipment_ids)
    errors: Dict[int, Any] = {}
    updated: List[int] = []

    from ..models import Address

    with transaction.atomic():
        for s in shipments:
            # If payload is only an id, treat it as assignment to an existing Address
            if 'id' in address_data and len(address_data.keys()) == 1:
                addr_id = address_data.get('id')
                try:
                    addr = Address.objects.get(pk=addr_id)
                except Address.DoesNotExist:
                    errors[s.pk] = {'id': [f'Address with id {addr_id} not found.']}
                    continue
                s.ship_from = addr
                s.save(update_fields=['ship_from', 'updated_at'])
                updated.append(s.pk)
                continue

            # Otherwise, clone the base address (use provided id as base if present)
            base_addr = s.ship_from
            if 'id' in address_data:
                try:
                    base_addr = Address.objects.get(pk=address_data.get('id'))
                except Address.DoesNotExist:
                    errors[s.pk] = {'id': [f'Address with id {address_data.get("id")} not found.']}
                    continue

            base = {
                'name': base_addr.name,
                'address_line1': base_addr.address_line1,
                'address_line2': base_addr.address_line2,
                'city': base_addr.city,
                'state': base_addr.state,
                'postal_code': base_addr.postal_code,
                'phone': base_addr.phone,
            }
            merged = {**base, **{k: v for k, v in address_data.items() if k != 'id'}}

            serializer = AddressSerializer(data=merged)
            if serializer.is_valid():
                new_addr = serializer.save()
                s.ship_from = new_addr
                s.save(update_fields=['ship_from', 'updated_at'])
                updated.append(s.pk)
            else:
                errors[s.pk] = serializer.errors

    found_ids = {s.pk for s in shipments}
    missing = [i for i in shipment_ids if i not in found_ids]
    for m in missing:
        errors[m] = {'shipment': ['Not found.']}

    return {'updated': updated, 'errors': errors}


def update_package(shipment_ids: List[int], package_data: Dict[str, Any]) -> Dict[str, Any]:
    shipments = _fetch_shipments(shipment_ids)
    errors: Dict[int, Any] = {}
    updated: List[int] = []

    with transaction.atomic():
        for s in shipments:
            serializer = PackageSerializer(s.package, data=package_data, partial=True)
            if serializer.is_valid():
                serializer.save()
                updated.append(s.pk)
            else:
                errors[s.pk] = serializer.errors

    found_ids = {s.pk for s in shipments}
    missing = [i for i in shipment_ids if i not in found_ids]
    for m in missing:
        errors[m] = {'shipment': ['Not found.']}

    return {'updated': updated, 'errors': errors}


def update_shipping_service(shipment_ids: List[int], shipping_service: str) -> Dict[str, Any]:
    shipments = _fetch_shipments(shipment_ids)
    errors: Dict[int, Any] = {}
    updated: List[int] = []

    with transaction.atomic():
        for s in shipments:
            try:
                price = calculate_price_for_package(shipping_service, s.package)
            except Exception as exc:
                errors[s.pk] = {'shipping_service': [str(exc)]}
                continue
            s.shipping_service = shipping_service
            s.price_cents = price
            s.save(update_fields=['shipping_service', 'price_cents', 'updated_at'])
            updated.append(s.pk)

    found_ids = {s.pk for s in shipments}
    missing = [i for i in shipment_ids if i not in found_ids]
    for m in missing:
        errors[m] = {'shipment': ['Not found.']}

    return {'updated': updated, 'errors': errors}


def delete_shipments(shipment_ids: List[int]) -> Dict[str, Any]:
    existing = list(Shipment.objects.filter(pk__in=shipment_ids).values_list('pk', flat=True))
    not_found = [i for i in shipment_ids if i not in existing]
    if existing:
        Shipment.objects.filter(pk__in=existing).delete()
    return {'deleted': list(existing), 'not_found': not_found}


def assign_shipping_service(shipment_id: int, shipping_service: str) -> Dict[str, Any]:
    """
    Assign a shipping service to a single shipment, recalculate price using package weight,
    and persist the changes. Returns {'updated': id, 'price_cents': int} or raises ValueError/ObjectDoesNotExist.
    """
    try:
        s = Shipment.objects.select_related('package').get(pk=shipment_id)
    except Shipment.DoesNotExist:
        raise ValueError("Shipment not found")

    try:
        price = calculate_price_for_package(shipping_service, s.package)
    except Exception as exc:
        raise ValueError(str(exc))

    s.shipping_service = shipping_service
    s.price_cents = price
    s.save(update_fields=['shipping_service', 'price_cents', 'updated_at'])
    return {'updated': s.pk, 'price_cents': price}