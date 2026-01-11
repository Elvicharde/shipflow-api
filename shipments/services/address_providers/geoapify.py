from __future__ import annotations
from .base import Provider


class Provider(Provider):
    name = 'geoapify'

    def verify(self, address, country_code=None):
        # Minimal, local second-line verification implementation.
        # If address has postal_code and city, return success.
        postal = (address.get('postal_code') or '').strip()
        city = (address.get('city') or '').strip()
        if postal and city:
            metadata = {
                'formatted': f"{address.get('address_line1', '')}, {address.get('city', '')} {postal}",
                'components': {
                    'city': city,
                    'postal_code': postal,
                    'state': address.get('state', ''),
                }
            }
            return self._ok(metadata=metadata, confidence=0.9)
        return self._fail('missing city or postal code')
