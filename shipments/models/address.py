from __future__ import annotations
from django.db import models


class Address(models.Model):
    """
    Generic address model suitable for both ship-from and ship-to usage.
    """
    name = models.CharField(max_length=255)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, null=True, blank=True, default=None)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, null=True, blank=True, default=None)
    postal_code = models.CharField(max_length=20)
    phone = models.CharField(max_length=32, null=True, blank=True, default=None)

    # Verification fields
    is_verified = models.BooleanField(default=False)
    verification_provider = models.CharField(max_length=64, null=True, blank=True, default=None)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_metadata = models.JSONField(null=True, blank=True, default=dict)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'address'
        verbose_name_plural = 'addresses'

    def __str__(self) -> str:
        return f'{self.name} — {self.city} {self.postal_code}'