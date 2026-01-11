from __future__ import annotations
from django.db import models


class Address(models.Model):
    """
    Generic address model suitable for both ship-from and ship-to usage.
    """
    name = models.CharField(max_length=255)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True, default='')
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, blank=True, default='')
    postal_code = models.CharField(max_length=20)
    phone = models.CharField(max_length=32, blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'address'
        verbose_name_plural = 'addresses'

    def __str__(self) -> str:
        return f'{self.name} — {self.city} {self.postal_code}'