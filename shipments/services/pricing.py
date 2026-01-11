from __future__ import annotations
from typing import Dict

from ..models import Package


# Deterministic price table (cents)
PRICE_TABLE: Dict[str, Dict[str, int]] = {
    'priority': {'label': 'Priority', 'base_cents': 500, 'per_ounce_cents': 10},
    'ground': {'label': 'Ground', 'base_cents': 300, 'per_ounce_cents': 5},
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


def calculate_price_cents(service: str, weight_ounces: int) -> int:
    """
    Calculate price in cents for a given service and weight in ounces.

    Price formula: total_cents = base_cents + per_ounce_cents * weight_ounces
    """
    if weight_ounces is None or int(weight_ounces) < 0:
        raise ValueError("weight_ounces must be a non-negative integer")
    cfg = get_service_config(service)
    return int(cfg['base_cents']) + int(cfg['per_ounce_cents']) * int(weight_ounces)


def calculate_price_for_package(service: str, package: Package) -> int:
    """
    Convenience wrapper that computes total weight in ounces from a Package
    and returns the calculated price in cents.
    """
    if not isinstance(package, Package):
        raise TypeError("package must be a Package instance")
    return calculate_price_cents(service, package.total_weight_ounces())