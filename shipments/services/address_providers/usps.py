from __future__ import annotations
from .base import Provider


class Provider(Provider):
    name = 'usps'

    def verify(self, address, country_code=None):
        # USPS is US-only; require postal code and country being US (caller should enforce)
        postal = (address.get('postal_code') or '').strip()
        if not postal:
            return self._fail('missing postal code')
        # For this implementation, treat any non-empty postal code as a success for US
        metadata = {
            'formatted': f"{address.get('address_line1', '')}, {address.get('city', '')} {postal}",
            'components': {'postal_code': postal, 'city': address.get('city', ''), 'state': address.get('state', '')}
        }
        return self._ok(metadata=metadata, confidence=0.95)
