from __future__ import annotations
from typing import Any, Dict, Tuple, Union

from ..models import Address, Package, Shipment
from ..serializers import AddressSerializer, PackageSerializer


def validate_row(row: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate sender, recipient, and package fields.
    Returns (is_valid, errors)
    """
    errors = {}

    # Sender address
    sender = row.get("data").get('ship_from', {})
    sender_required = ['name', 'address_line1', 'city', "postal_code"]
    for field in sender_required:
        if not sender.get(field):
            errors.setdefault('ship_from', {})[field] = 'This field is required.'

    # Recipient address
    recipient = row.get("data").get('ship_to', {})
    recipient_required = ['name', 'address_line1', 'city', "postal_code", 'phone']
    for field in recipient_required:
        if not recipient.get(field):
            errors.setdefault('ship_to', {})[field] = 'This field is required.'

    # Package
    package = row.get("data").get('package', {})
    package_required = ['length_in', 'width_in', 'height_in', 'weight_lbs', 'weight_oz']
    for field in package_required:
        if not package.get(field):
            errors.setdefault('package', {})[field] = 'This field is required.'

    is_valid = not errors
    return is_valid, errors



def address_validation(
    address: Union[Address, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Validate an address (model instance or dict) and return serializer-style errors dict.
    Empty dict means valid.
    """
    if isinstance(address, dict):
        ser = AddressSerializer(data=address)
        ser.is_valid(raise_exception=False)
        return ser.errors
    # model instance: check required fields
    errors: Dict[str, Any] = {}
    for field in ("name", "address_line1", "city", "postal_code"):
        if not getattr(address, field, None):
            errors.setdefault(field, []).append("This field is required.")
    return errors


def package_validation(
    package: Union[Package, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Validate a package (model instance or dict) and return serializer-style errors dict.
    Empty dict means valid.
    """
    if isinstance(package, dict):
        ser = PackageSerializer(data=package)
        ser.is_valid(raise_exception=False)
        return ser.errors

    # model instance checks
    errors: Dict[str, Any] = {}

    # weight
    total_oz = int(getattr(package, "weight_lbs", 0)) * 16 + int(getattr(package, "weight_oz", 0))
    if total_oz == 0:
        errors.setdefault("weight", []).append("Total weight must be greater than zero.")
    if getattr(package, "weight_oz", 0) < 0 or getattr(package, "weight_oz", 0) > 15:
        errors.setdefault("weight_oz", []).append("weight_oz must be between 0 and 15.")

    # dimensions (non-negative if present)
    for dim in ("length_in", "width_in", "height_in"):
        val = getattr(package, dim, None)
        if val is not None:
            try:
                if val < 0:
                    errors.setdefault(dim, []).append(f"{dim} must be >= 0.")
            except TypeError:
                errors.setdefault(dim, []).append(f"{dim} must be a number.")
    return errors


def shipment_ready(
    shipment: Union[Shipment, Dict[str, Any]]
) -> Tuple[bool, Dict[str, Any]]:
    """
    Determine readiness of a shipment based on address and package completeness.
    Returns (is_ready, errors) where errors is a dict with keys: ship_from, ship_to, package.
    """
    errors: Dict[str, Any] = {"ship_from": {}, "ship_to": {}, "package": {}}

    if isinstance(shipment, dict):
        ship_from = shipment.get("ship_from", {})
        ship_to = shipment.get("ship_to", {})
        package = shipment.get("package", {})
        errors["ship_from"] = address_validation(ship_from)
        errors["ship_to"] = address_validation(ship_to)
        errors["package"] = package_validation(package)
    else:
        errors["ship_from"] = address_validation(shipment.ship_from)
        errors["ship_to"] = address_validation(shipment.ship_to)
        errors["package"] = package_validation(shipment.package)

    # Compact empty error dicts to {}
    ready = True
    for k in list(errors.keys()):
        if not errors[k]:
            errors[k] = {}
        else:
            ready = False

    return ready, errors