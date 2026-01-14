from __future__ import annotations
import hashlib
from core.logger import get_logger
from datetime import datetime
from importlib import import_module
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.cache import cache

logger = get_logger()

CACHE_TTL = getattr(settings, 'ADDRESS_VERIFICATION', {}).get('CACHE_TTL', 30 * 24 * 60 * 60)
CIRCUIT_THRESHOLD = getattr(settings, 'ADDRESS_VERIFICATION', {}).get('CIRCUIT_BREAKER_THRESHOLD', 5)
CIRCUIT_TIMEOUT = getattr(settings, 'ADDRESS_VERIFICATION', {}).get('CIRCUIT_BREAKER_TIMEOUT', 300)

PROVIDER_MODULES = {
    'usps': 'shipments.services.address_providers.usps',
    'geoapify': 'shipments.services.address_providers.geoapify',
    'here': 'shipments.services.address_providers.here',
    'mapbox': 'shipments.services.address_providers.mapbox',
    'google': 'shipments.services.address_providers.google',
}


def _normalize_address_key(address: Dict[str, Any], country_code: Optional[str]) -> str:
    parts = [
        (address.get('name') or '').strip().lower(),
        (address.get('address_line1') or '').strip().lower(),
        (address.get('address_line2') or '').strip().lower(),
        (address.get('city') or '').strip().lower(),
        (address.get('state') or '').strip().lower(),
        (address.get('postal_code') or '').strip().lower(),
        (country_code or '').strip().lower(),
    ]
    key = '|'.join(parts)
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


class AddressVerificationService:
    """Verify addresses using a prioritized chain of providers with caching, rate-limiting and circuit-breaking."""

    def __init__(self):
        self.chain = getattr(settings, 'ADDRESS_VERIFICATION_CHAIN', [])

    def _get_cached(self, norm_key: str) -> Optional[Dict[str, Any]]:
        return cache.get(f'verified_addr:{norm_key}')

    def _set_cached(self, norm_key: str, result: Dict[str, Any]):
        cache.set(f'verified_addr:{norm_key}', result, timeout=CACHE_TTL)

    def _circuit_open(self, provider: str) -> bool:
        return cache.get(f'circuit_open:{provider}', False)

    def _record_failure(self, provider: str):
        key = f'failures:{provider}'
        failures = cache.get(key, 0) + 1
        cache.set(key, failures, timeout=CIRCUIT_TIMEOUT * 2)
        if failures >= CIRCUIT_THRESHOLD:
            cache.set(f'circuit_open:{provider}', True, timeout=CIRCUIT_TIMEOUT)
            logger.warning('Circuit opened for provider %s after %d failures', provider, failures)

    def _reset_failures(self, provider: str):
        cache.delete(f'failures:{provider}')
        cache.delete(f'circuit_open:{provider}')

    def verify_address(self, address: Dict[str, Any], country_code: Optional[str] = None) -> Dict[str, Any]:
        """Main entry point to verify address. Returns normalized result dict.

        Result format:
        {
            'ok': True|False,
            'provider': 'geoapify',
            'verified_at': datetime,
            'metadata': {...},
            'confidence': 0.0-1.0,
            'suggestions': [...],
            'error': 'message'  # on failure
        }
        """


        request_id = None
        user_id = None
        operation = "address_verification"
        entity = "address"
        norm = _normalize_address_key(address, country_code)
        cached = self._get_cached(norm)
        if cached:
            logger.info(
                "Address verification cache hit",
                extra={
                    "operation": operation,
                    "entity": entity,
                    "status": "cache_hit",
                    "request_id": request_id,
                    "user_id": user_id,
                },
            )
            return cached

        errors = []

        import time
        for entry in self.chain:
            name = entry.get('name')
            if not entry.get('enabled'):
                continue
            # country restrictions
            countries = entry.get('countries', ['*'])
            if countries != ['*'] and country_code and country_code.upper() not in [c.upper() for c in countries]:
                continue

            if self._circuit_open(name):
                logger.warning(
                    "Provider circuit open, skipping",
                    extra={
                        "operation": operation,
                        "entity": entity,
                        "provider": name,
                        "status": "circuit_open",
                        "request_id": request_id,
                        "user_id": user_id,
                    },
                )
                continue

            module_path = PROVIDER_MODULES.get(name)
            if not module_path:
                continue

            try:
                module = import_module(module_path)
                ProviderClass = getattr(module, 'Provider')
                provider = ProviderClass()
            except Exception as exc:
                logger.error(
                    "Failed to load provider module",
                    extra={
                        "operation": operation,
                        "entity": entity,
                        "provider": name,
                        "status": "failure",
                        "error_code": "provider_import_error",
                        "error_message": str(exc),
                        "request_id": request_id,
                        "user_id": user_id,
                    },
                )
                self._record_failure(name)
                errors.append({name: str(exc)})
                continue


            try:
                start = time.time()
                res = provider.verify(address=address, country_code=country_code)
                latency = time.time() - start
            except Exception as exc:
                logger.error(
                    "Provider call failed",
                    extra={
                        "operation": operation,
                        "entity": entity,
                        "provider": name,
                        "status": "failure",
                        "error_code": "provider_call_error",
                        "error_message": str(exc),
                        "request_id": request_id,
                        "user_id": user_id,
                    },
                )
                self._record_failure(name)
                errors.append({name: str(exc)})
                continue


            if not isinstance(res, dict):
                logger.error(
                    "Invalid provider response",
                    extra={
                        "operation": operation,
                        "entity": entity,
                        "provider": name,
                        "status": "failure",
                        "error_code": "invalid_provider_response",
                        "request_id": request_id,
                        "user_id": user_id,
                    },
                )
                self._record_failure(name)
                errors.append({name: 'invalid provider response'})
                continue


            if res.get('ok'):
                result = {
                    'ok': True,
                    'provider': name,
                    'verified_at': res.get('verified_at', datetime.utcnow()),
                    'metadata': res.get('metadata', {}),
                    'confidence': res.get('confidence', 1.0),
                    'suggestions': res.get('suggestions', []),
                }
                self._set_cached(norm, result)
                self._reset_failures(name)
                logger.info(
                    "Address verified",
                    extra={
                        "operation": operation,
                        "entity": entity,
                        "provider": name,
                        "status": "success",
                        "latency_ms": int(latency * 1000),
                        "request_id": request_id,
                        "user_id": user_id,
                    },
                )
                return result
            else:
                self._record_failure(name)
                logger.warning(
                    "Provider verification failed",
                    extra={
                        "operation": operation,
                        "entity": entity,
                        "provider": name,
                        "status": "failure",
                        "error_code": "verification_failed",
                        "error_message": res.get('error', 'verification failed'),
                        "request_id": request_id,
                        "user_id": user_id,
                    },
                )
                errors.append({name: res.get('error', 'verification failed')})

        # nothing succeeded
        logger.error(
            "All providers failed for address",
            extra={
                "operation": operation,
                "entity": entity,
                "status": "failure",
                "error_code": "all_providers_failed",
                "error_message": str(errors),
                "request_id": request_id,
                "user_id": user_id,
            },
        )
        return {'ok': False, 'errors': errors}
