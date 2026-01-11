from __future__ import annotations
from .base import Provider


class Provider(Provider):
    name = 'mapbox'

    def verify(self, address, country_code=None):
        # Minimal heuristic: accept if address_line1 present
        if address.get('address_line1'):
            metadata = {'formatted': address.get('address_line1'), 'components': {'city': address.get('city','')}}
            return self._ok(metadata=metadata, confidence=0.8)
        return self._fail('missing address line 1')
