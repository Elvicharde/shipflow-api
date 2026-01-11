from __future__ import annotations
import uuid
from django.db import models

class UploadSessionStatus(models.TextChoices):
    UPLOADED = 'uploaded', 'Uploaded'
    REVIEWED = 'reviewed', 'Reviewed'
    SHIPPING_SELECTED = 'shipping_selected', 'Shipping Selected'
    PURCHASED = 'purchased', 'Purchased'

class UploadSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(
        max_length=32,
        choices=UploadSessionStatus.choices,
        default=UploadSessionStatus.UPLOADED,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'upload session'
        verbose_name_plural = 'upload sessions'

    def __str__(self) -> str:
        return f'UploadSession {self.id} ({self.status})'