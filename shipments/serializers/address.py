from __future__ import annotations
from rest_framework import serializers

from ..models import Address


class AddressSerializer(serializers.ModelSerializer):
    """
    Serializer for Address with validation for required fields.
    Required: name, address_line1, city, postal_code
    """
    class Meta:
        model = Address
        fields = [
            'id',
            'name',
            'address_line1',
            'address_line2',
            'city',
            'state',
            'postal_code',
            'phone',
            'is_verified',
            'verification_provider',
            'verified_at',
            'verification_metadata',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        # Enforce required fields on create / full update.
        if not getattr(self, 'partial', False):
            required = ['name', 'address_line1', 'city', 'postal_code']
            errors = {}
            for field in required:
                if not data.get(field):
                    errors[field] = 'This field is required.'
            if errors:
                raise serializers.ValidationError(errors)
        return data