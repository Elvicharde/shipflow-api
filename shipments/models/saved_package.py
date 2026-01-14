from __future__ import annotations
from django.db import models

from .package import Package


class SavedPackage(models.Model):
    """
    Reusable preset for Packages.
    Stores a friendly label and references a Package instance.
    """
    label = models.CharField(max_length=128)
    package = models.ForeignKey(
        Package, on_delete=models.CASCADE, related_name='saved_packages'
    )
    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'saved package'
        verbose_name_plural = 'saved packages'
        indexes = [
            models.Index(fields=['label']),
        ]

    def __str__(self) -> str:
        return f'{self.label} — {self.package.sku or self.package.pk}'