from __future__ import annotations
from decimal import Decimal

from rest_framework import serializers

from ..models import Package


class PackageSerializer(serializers.ModelSerializer):
    """
    Serializer for Package with numeric validation for dimensions and weight.
    - Dimensions (length_in, width_in, height_in) must be >= 0 when provided.
    - weight_lbs must be >= 0
    - weight_oz must be between 0 and 15
    - total weight (lbs + oz) must be > 0
    """
    class Meta:
        model = Package
        fields = [
            'id',
            'sku',
            'length_in',
            'width_in',
            'height_in',
            'weight_lbs',
            'weight_oz',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def _is_non_negative(self, value):
        try:
            return Decimal(value) >= 0
        except Exception:
            return False

    def validate_length_in(self, value):
        if value is None:
            return value
        if not self._is_non_negative(value):
            raise serializers.ValidationError('length_in must be a non-negative number.')
        return value

    def validate_width_in(self, value):
        if value is None:
            return value
        if not self._is_non_negative(value):
            raise serializers.ValidationError('width_in must be a non-negative number.')
        return value

    def validate_height_in(self, value):
        if value is None:
            return value
        if not self._is_non_negative(value):
            raise serializers.ValidationError('height_in must be a non-negative number.')
        return value

    def validate_weight_lbs(self, value):
        if value is None:
            return value
        if int(value) < 0:
            raise serializers.ValidationError('weight_lbs must be >= 0.')
        return int(value)

    def validate_weight_oz(self, value):
        if value is None:
            return value
        oz = int(value)
        if oz < 0 or oz > 15:
            raise serializers.ValidationError('weight_oz must be between 0 and 15.')
        return oz

    def validate(self, data):
        lbs = data.get('weight_lbs', getattr(self.instance, 'weight_lbs', 0) if self.instance else 0)
        oz = data.get('weight_oz', getattr(self.instance, 'weight_oz', 0) if self.instance else 0)
        if int(lbs) * 16 + int(oz) == 0:
            raise serializers.ValidationError('Total weight must be greater than zero.')
        return data