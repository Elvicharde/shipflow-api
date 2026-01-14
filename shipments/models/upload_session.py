from __future__ import annotations
import uuid
from django.db import models

class UploadSessionStatus(models.TextChoices):
    UPLOADED = 'uploaded', 'Uploaded'
    VALIDATING = 'validating', 'Validating'
    VALIDATED = 'validated', 'Validated'
    PARTIAL_VALID = 'partial_valid', 'Partial Valid'
    VALID = 'valid', 'Valid'
    INVALID = 'invalid', 'Invalid'
    FAILED = 'failed', 'Failed'
    READY_FOR_PURCHASE = 'ready_for_purchase', 'Ready for Purchase'
    PURCHASED = 'purchased', 'Purchased'

class UploadSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=255, null=True, blank=True, default=None)
    status = models.CharField(
        max_length=32,
        choices=UploadSessionStatus.choices,
        default=UploadSessionStatus.UPLOADED,
    )
    rows_total = models.PositiveIntegerField(null=True, blank=True, default=None)
    rows_valid = models.PositiveIntegerField(null=True, blank=True, default=None)
    rows_invalid = models.PositiveIntegerField(null=True, blank=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'upload session'
        verbose_name_plural = 'upload sessions'

    def __str__(self) -> str:
        return f'UploadSession {self.id} ({self.status})'