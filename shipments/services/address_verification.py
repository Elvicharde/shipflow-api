from __future__ import annotations
import hashlib
import logging
from datetime import datetime
from importlib import import_module
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

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

        norm = _normalize_address_key(address, country_code)
        cached = self._get_cached(norm)
        if cached:
            logger.debug('Address verification cache hit')
            return cached

        errors = []

        for entry in self.chain:
            name = entry.get('name')
            if not entry.get('enabled'):
                continue
            # country restrictions
            countries = entry.get('countries', ['*'])
            if countries != ['*'] and country_code and country_code.upper() not in [c.upper() for c in countries]:
                continue

            if self._circuit_open(name):
                logger.info('Skipping provider %s because circuit is open', name)
                continue

            module_path = PROVIDER_MODULES.get(name)
            if not module_path:
                continue
            try:
                module = import_module(module_path)
                ProviderClass = getattr(module, 'Provider')
                provider = ProviderClass()
            except Exception as exc:
                logger.exception('Failed to load provider module %s: %s', module_path, exc)
                self._record_failure(name)
                errors.append({name: str(exc)})
                continue

            try:
                # Each provider verifies and returns a dict
                res = provider.verify(address=address, country_code=country_code)
            except Exception as exc:
                logger.exception('Provider %s raised exception: %s', name, exc)
                self._record_failure(name)
                errors.append({name: str(exc)})
                continue

            if not isinstance(res, dict):
                self._record_failure(name)
                errors.append({name: 'invalid provider response'})
                continue

            if res.get('ok'):
                # success: normalize and cache result
                result = {
                    'ok': True,
                    'provider': name,
                    'verified_at': res.get('verified_at', datetime.utcnow()),
                    'metadata': res.get('metadata', {}),
                    'confidence': res.get('confidence', 1.0),
                    'suggestions': res.get('suggestions', []),
                }
                self._set_cached(norm, result)
                # reset failure count on success
                self._reset_failures(name)
                logger.info('Address verified by %s', name)
                return result
            else:
                # record failure and continue to next provider
                self._record_failure(name)
                errors.append({name: res.get('error', 'verification failed')})

        # nothing succeeded
        logger.warning('All providers failed for address: %s', errors)
        return {'ok': False, 'errors': errors}
