from __future__ import annotations

from django.db import models

from .upload_session import UploadSession
from .address import Address
from .package import Package


class ShipmentStatus(models.TextChoices):
    CREATED = 'created', 'Created'
    VALIDATED = 'validated', 'Validated'
    PARTIAL_VALID = 'partial_valid', 'Partial Valid'
    INVALID = 'invalid', 'Invalid'
    READY_FOR_PURCHASE = 'ready_for_purchase', 'Ready for Purchase'
    PURCHASED = 'purchased', 'Purchased'
    CANCELLED = 'cancelled', 'Cancelled'


class ValidationStatus(models.TextChoices):
    VALID = 'valid', 'Valid'
    PARTIAL = 'partial', 'Partial'
    INVALID = 'invalid', 'Invalid'
    BLANK = 'blank', 'Blank'


class PricingStatus(models.TextChoices):
    PRICED = 'priced', 'Priced'
    UNPRICED = 'unpriced', 'Unpriced'
    ERROR = 'error', 'Error'


class Shipment(models.Model):
    """
    Shipment links an UploadSession to a ship-from and ship-to Address and a Package.
    Stores shipping service selection, price (in cents) and an optional order number.
    """
    upload_session = models.ForeignKey(
        UploadSession, on_delete=models.CASCADE, related_name='shipments'
    )
    row_number = models.PositiveIntegerField(null=True, blank=True, help_text="CSV row number for upload tracking")
    ship_from = models.ForeignKey(
        Address, on_delete=models.PROTECT, related_name='shipments_from'
    )
    ship_to = models.ForeignKey(
        Address, on_delete=models.PROTECT, related_name='shipments_to'
    )
    package = models.ForeignKey(
        Package, on_delete=models.PROTECT, related_name='shipments'
    )

    shipping_service = models.CharField(max_length=128, null=True, blank=True, default=None)
    shipping_option = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        default=None,
        help_text="Shipping option: 'ground' or 'priority'"
    )
    price_cents = models.PositiveIntegerField(null=True, blank=True, default=None)
    order_number = models.CharField(max_length=128, null=True, blank=True, default=None)

    status = models.CharField(
        max_length=32,
        choices=ShipmentStatus.choices,
        default=ShipmentStatus.CREATED,
    )
    validation_status = models.CharField(
        max_length=16,
        choices=ValidationStatus.choices,
        default=ValidationStatus.INVALID,
    )
    validation_errors = models.JSONField(null=True, blank=True, default=dict)
    pricing_status = models.CharField(
        max_length=16,
        choices=PricingStatus.choices,
        default=PricingStatus.UNPRICED,
    )
    locked = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'shipment'
        verbose_name_plural = 'shipments'

    def __str__(self) -> str:
        return f'Shipment {self.pk} — {self.status}'