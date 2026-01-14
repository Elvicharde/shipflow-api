from __future__ import annotations
from typing import Dict, Any, Tuple

from ..models import Package


# Deterministic price table (cents)
PRICE_TABLE: Dict[str, Dict[str, int]] = {
    'priority': {'base_cents': 500, 'per_ounce_cents': 10},
    'ground': {'base_cents': 300, 'per_ounce_cents': 5},
}


def _normalize_service(service: str) -> str:
    if not service:
        raise ValueError("service must be provided")
    return service.strip().lower()


def get_service_config(service: str) -> Dict[str, int]:
    """
    Return price config for the given service name (case-insensitive).
    Raises ValueError for unknown services.
    """
    key = _normalize_service(service)
    try:
        return PRICE_TABLE[key]
    except KeyError:
        raise ValueError(f"Unknown shipping service: {service}")


def calculate_price(service: str, weight: int, dimensions: Dict[str, Any]) -> Tuple[int, str]:
    """
    Calculate price for a shipment.
    - service: must be provided and valid
    - weight: in ounces
    - dimensions: dict with length, width, height
    Returns (price_cents, currency)
    """
    if not service:
        raise ValueError("Shipping service must be provided")
    if weight is None or weight <= 0:
        raise ValueError("Weight must be greater than zero")
    if not all(dimensions.values()):
        raise ValueError("All package dimensions must be provided")

    config = PRICE_TABLE.get(service.lower())
    if not config:
        raise ValueError(f"Unknown shipping service: {service}")

    price = config['base_cents'] + config['per_ounce_cents'] * int(weight)
    return price, 'USD'


def calculate_price_for_package(service: str, package: Package) -> int:
    """
    Convenience wrapper that computes total weight in ounces from a Package
    and returns the calculated price in cents.
    """
    if not isinstance(package, Package):
        raise TypeError("package must be a Package instance")
    dimensions = {
        'length': getattr(package, 'length_in', None),
        'width': getattr(package, 'width_in', None),
        'height': getattr(package, 'height_in', None),
    }
    price_cents, _currency = calculate_price(
        service,
        package.total_weight_ounces(),
        dimensions
    )
    return price_cents