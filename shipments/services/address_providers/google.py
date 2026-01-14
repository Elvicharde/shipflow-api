from __future__ import annotations
from .base import Provider


class Provider(Provider):
    name = 'google'

    def verify(self, address, country_code=None):
        # Paid global fallback. Here, use a permissive heuristic.
        if address.get('postal_code') or address.get('address_line1'):
            metadata = {'formatted': f"{address.get('address_line1','')}, {address.get('city','')}", 'components': {'postal_code': address.get('postal_code','')}}
            return self._ok(metadata=metadata, confidence=0.75)
        return self._fail('insufficient address information')
