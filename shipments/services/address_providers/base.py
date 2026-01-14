from __future__ import annotations
from typing import Any, Dict, Optional
from datetime import datetime

from django.conf import settings


class Provider:
    """Abstract provider base class."""

    name = 'base'

    def __init__(self):
        self.settings = getattr(settings, 'ADDRESS_VERIFICATION', {})

    def verify(self, address: Dict[str, Any], country_code: Optional[str] = None) -> Dict[str, Any]:
        """Override in subclass. Return dict consistent with AddressVerificationService expectations."""
        raise NotImplementedError("Provider must implement verify()")

    def _ok(self, metadata: Dict[str, Any], confidence: float = 1.0, suggestions: Optional[list] = None) -> Dict[str, Any]:
        return {
            'ok': True,
            'verified_at': datetime.utcnow(),
            'metadata': metadata,
            'confidence': confidence,
            'suggestions': suggestions or [],
        }

    def _fail(self, message: str) -> Dict[str, Any]:
        return {'ok': False, 'error': message}
