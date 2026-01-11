from __future__ import annotations
from django.db import models

from .address import Address


class SavedAddress(models.Model):
    """
    Reusable preset for ship-from addresses.
    Stores a friendly label and references an Address instance.
    """
    label = models.CharField(max_length=128)
    address = models.ForeignKey(
        Address, on_delete=models.CASCADE, related_name='saved_addresses'
    )
    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'saved address'
        verbose_name_plural = 'saved addresses'
        indexes = [
            models.Index(fields=['label']),
        ]

    def __str__(self) -> str:
        return f'{self.label} — {self.address.city} {self.address.postal_code}'