from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
import csv
import io
import logging

from shipments.models.upload_session import UploadSession

logger = logging.getLogger(__name__)


class UploadSessionSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and viewing UploadSession objects.

    Responsibilities:
    - Validate that uploaded file is a CSV
    - Ensure CSV has at least two header rows + one data row
    - Ensure data rows contain columns 0–22 (23 columns)
    - Keep serializer thin: create the model and hand off processing to the upload service
    """

    file = serializers.FileField(write_only=True, required=True)
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    status = serializers.CharField(read_only=True)
    rows_total = serializers.IntegerField(read_only=True)
    rows_valid = serializers.IntegerField(read_only=True)
    rows_invalid = serializers.IntegerField(read_only=True)

    class Meta:
        model = UploadSession
        fields = (
            "id",
            "file",
            "owner",
            "status",
            "rows_total",
            "rows_valid",
            "rows_invalid",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "rows_total",
            "rows_valid",
            "rows_invalid",
            "created_at",
            "updated_at",
        )

    def validate_file(self, file):
        filename = getattr(file, "name", "")
        if not filename.lower().endswith(".csv"):
            raise serializers.ValidationError(_("Uploaded file must be a CSV"))

        try:
            content = file.read().decode("utf-8-sig", errors="replace")
            lines = content.splitlines()
            if len(lines) <= 2:
                raise serializers.ValidationError(
                    _("CSV must contain at least one data row after two header rows")
                )

            reader = csv.reader(io.StringIO(content))
            # Skip two header rows
            next(reader, None)
            next(reader, None)
            first_data = next(reader, None)
            if first_data is None:
                raise serializers.ValidationError(_("CSV must contain at least one data row"))

            # Enforce mapping of columns 0–22 => 23 columns minimum
            if len(first_data) < 23:
                raise serializers.ValidationError(
                    _("CSV rows must have at least 23 columns (columns 0–22)")
                )
        except UnicodeDecodeError:
            raise serializers.ValidationError(_("Unable to decode CSV file (invalid encoding)"))
        finally:
            # Reset file pointer for later storage/processing
            try:
                file.seek(0)
            except Exception:
                logger.debug("Could not reset file pointer after validation", exc_info=True)

        return file

    def create(self, validated_data):
        # Attach owner (HiddenField ensures CurrentUserDefault) and persist the session
        owner = validated_data.pop("owner", None)
        session = UploadSession.objects.create(owner=owner, **validated_data)

        # Enqueue processing to keep serializers/views thin.
        # The enqueue function is expected in shipments.services.upload
        try:
            from shipments.services.upload import enqueue_upload

            enqueue_upload(session)
        except Exception:
            logger.exception("Failed to enqueue upload processing for session %s", session.pk)

        return session