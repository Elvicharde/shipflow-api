from __future__ import annotations
from typing import Dict, List, Any

from django.db import transaction


from ..models import Shipment
from ..serializers import AddressSerializer, PackageSerializer
from .pricing import calculate_price_for_package
from django.db import transaction
from shipments.models import Shipment
from core.logger import get_logger

logger = get_logger()

# Backend price logic matching frontend Step4Review.simulateCost
def calculate_step4review_price(service: str, option: str) -> float:
    base = 8 if option == 'priority' else 5
    if service in ('UPS', 'FedEx'):
        base += 2
    elif service == 'DHL':
        base += 1
    return float(base)

# Bulk update shipping service and option for multiple shipments
@transaction.atomic
def bulk_update_shipping_service_and_option(session, shipment_updates):
    """
    shipment_updates: list of dicts with keys: shipment_id, shipping_service, shipping_option
    Update each shipment individually using assign_shipping_service.
    """
    request_id = None
    user_id = None
    operation = "bulk_update_shipping_service_and_option"
    entity = "shipment"
    logger.info(
        "Bulk update shipping service/option started",
        extra={
            "operation": operation,
            "entity": entity,
            "status": "start",
            "count": len(shipment_updates) if shipment_updates else 0,
            "request_id": request_id,
            "user_id": user_id,
        },
    )
    if not shipment_updates:
        return []
    updated = []
    failed = 0
    for upd in shipment_updates:
        try:
            shipment = Shipment.objects.get(pk=upd['shipment_id'], upload_session=session)
            from shipments.services.shipment_update import assign_shipping_service_option
            assign_shipping_service_option(shipment, upd['shipping_service'], upd.get('shipping_option'))
            price = calculate_step4review_price(upd['shipping_service'], upd.get('shipping_option', 'priority'))
            shipment.price_cents = int(price * 100)
            shipment.save()
            updated.append(shipment)
        except Exception as exc:
            failed += 1
            logger.error(
                "Bulk update failed for shipment",
                extra={
                    "operation": operation,
                    "entity": entity,
                    "shipment_id": upd.get('shipment_id'),
                    "status": "failure",
                    "error_code": "bulk_update_error",
                    "error_message": str(exc),
                    "request_id": request_id,
                    "user_id": user_id,
                },
            )
    logger.info(
        "Bulk update shipping service/option completed",
        extra={
            "operation": operation,
            "entity": entity,
            "status": "success" if failed == 0 else ("partial" if updated else "failure"),
            "updated_count": len(updated),
            "failed_count": failed,
            "request_id": request_id,
            "user_id": user_id,
        },
    )
    return updated



def _fetch_shipments(ids: List[int]) -> List[Shipment]:
    return list(Shipment.objects.filter(pk__in=ids).select_related('ship_from', 'package'))


def update_ship_from(shipment_ids: List[int], address_data: Dict[str, Any]) -> Dict[str, Any]:
    request_id = None
    user_id = None
    operation = "bulk_update_ship_from"
    entity = "shipment"
    logger.info(
        "Bulk update ship_from started",
        extra={
            "operation": operation,
            "entity": entity,
            "status": "start",
            "count": len(shipment_ids),
            "request_id": request_id,
            "user_id": user_id,
        },
    )
    shipments = _fetch_shipments(shipment_ids)
    errors: Dict[int, Any] = {}
    updated: List[int] = []

    from ..models import Address

    with transaction.atomic():
        for s in shipments:
            if 'id' in address_data and len(address_data.keys()) == 1:
                addr_id = address_data.get('id')
                try:
                    addr = Address.objects.get(pk=addr_id)
                except Address.DoesNotExist as exc:
                    errors[s.pk] = {'id': [f'Address with id {addr_id} not found.']}
                    logger.error(
                        "Ship_from update failed: address not found",
                        extra={
                            "operation": operation,
                            "entity": entity,
                            "shipment_id": s.pk,
                            "status": "failure",
                            "error_code": "address_not_found",
                            "error_message": str(exc),
                            "request_id": request_id,
                            "user_id": user_id,
                        },
                    )
                    continue
                s.ship_from = addr
                s.save(update_fields=['ship_from', 'updated_at'])
                updated.append(s.pk)
                continue

            base_addr = s.ship_from
            if 'id' in address_data:
                try:
                    base_addr = Address.objects.get(pk=address_data.get('id'))
                except Address.DoesNotExist as exc:
                    errors[s.pk] = {'id': [f'Address with id {address_data.get("id")} not found.']}
                    logger.error(
                        "Ship_from update failed: base address not found",
                        extra={
                            "operation": operation,
                            "entity": entity,
                            "shipment_id": s.pk,
                            "status": "failure",
                            "error_code": "base_address_not_found",
                            "error_message": str(exc),
                            "request_id": request_id,
                            "user_id": user_id,
                        },
                    )
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
                logger.error(
                    "Ship_from update failed: serializer invalid",
                    extra={
                        "operation": operation,
                        "entity": entity,
                        "shipment_id": s.pk,
                        "status": "failure",
                        "error_code": "serializer_invalid",
                        "error_message": str(serializer.errors),
                        "request_id": request_id,
                        "user_id": user_id,
                    },
                )

    found_ids = {s.pk for s in shipments}
    missing = [i for i in shipment_ids if i not in found_ids]
    for m in missing:
        errors[m] = {'shipment': ['Not found.']}
        logger.error(
            "Ship_from update failed: shipment not found",
            extra={
                "operation": operation,
                "entity": entity,
                "shipment_id": m,
                "status": "failure",
                "error_code": "shipment_not_found",
                "request_id": request_id,
                "user_id": user_id,
            },
        )

    logger.info(
        "Bulk update ship_from completed",
        extra={
            "operation": operation,
            "entity": entity,
            "status": "success" if len(errors) == 0 else ("partial" if updated else "failure"),
            "updated_count": len(updated),
            "failed_count": len(errors),
            "request_id": request_id,
            "user_id": user_id,
        },
    )
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