from __future__ import annotations
from decimal import Decimal

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Package(models.Model):
    """
    Physical package representation.

    - SKU: optional product identifier
    - Dimensions in inches (length, width, height)
    - Weight as pounds + ounces (oz < 16)
    """
    sku = models.CharField(max_length=64, null=True, blank=True, default=None)

    length_in = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    width_in = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    height_in = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    weight_lbs = models.PositiveIntegerField(null=True, blank=True, default=None)
    weight_oz = models.PositiveIntegerField(
        null=True, blank=True, default=None,
        validators=[MaxValueValidator(15)]
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'package'
        verbose_name_plural = 'packages'

    def __str__(self) -> str:
        return f'Package {self.sku or self.pk} — {self.total_weight_ounces()} oz'

    def total_weight_ounces(self) -> int:
        return (int(self.weight_lbs or 0) * 16) + int(self.weight_oz or 0)