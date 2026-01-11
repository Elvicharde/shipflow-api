from __future__ import annotations
from .base import Provider


class Provider(Provider):
    name = 'here'

    def verify(self, address, country_code=None):
        # Minimal heuristic: success if postal or city present
        postal = (address.get('postal_code') or '').strip()
        city = (address.get('city') or '').strip()
        if postal or city:
            metadata = {
                'formatted': f"{address.get('address_line1','')}, {address.get('city','')} {postal}",
                'components': {'postal_code': postal, 'city': city, 'state': address.get('state', '')}
            }
            return self._ok(metadata=metadata, confidence=0.85)
        return self._fail('insufficient address data')
