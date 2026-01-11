from __future__ import annotations

from django.db import models

from .upload_session import UploadSession
from .address import Address
from .package import Package


class ShipmentStatus(models.TextChoices):
    CREATED = 'created', 'Created'
    VALIDATED = 'validated', 'Validated'
    SHIPPING_SELECTED = 'shipping_selected', 'Shipping Selected'
    PURCHASED = 'purchased', 'Purchased'
    CANCELLED = 'cancelled', 'Cancelled'


class Shipment(models.Model):
    """
    Shipment links an UploadSession to a ship-from and ship-to Address and a Package.
    Stores shipping service selection, price (in cents) and an optional order number.
    """
    upload_session = models.ForeignKey(
        UploadSession, on_delete=models.CASCADE, related_name='shipments'
    )
    ship_from = models.ForeignKey(
        Address, on_delete=models.PROTECT, related_name='shipments_from'
    )
    ship_to = models.ForeignKey(
        Address, on_delete=models.PROTECT, related_name='shipments_to'
    )
    package = models.ForeignKey(
        Package, on_delete=models.PROTECT, related_name='shipments'
    )

    shipping_service = models.CharField(max_length=128, blank=True, default='')
    price_cents = models.PositiveIntegerField(null=True, blank=True)
    order_number = models.CharField(max_length=128, blank=True, default='')

    status = models.CharField(
        max_length=32,
        choices=ShipmentStatus.choices,
        default=ShipmentStatus.CREATED,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'shipment'
        verbose_name_plural = 'shipments'

    def __str__(self) -> str:
        return f'Shipment {self.pk} — {self.status}'