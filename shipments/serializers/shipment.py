from __future__ import annotations
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ..models import Shipment, UploadSession, Address, Package
from .address import AddressSerializer
from .package import PackageSerializer


class ShipmentReadSerializer(serializers.ModelSerializer):
    ship_from = AddressSerializer(read_only=True)
    ship_to = AddressSerializer(read_only=True)
    package = PackageSerializer(read_only=True)
    upload_session = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Shipment
        fields = [
            'id',
            'upload_session',
            'ship_from',
            'ship_to',
            'package',
            'shipping_service',
            'shipping_option',
            'price_cents',
            'order_number',
            'status',
            'validation_status',
            'validation_errors',
            'pricing_status',
            'locked',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class ShipmentWriteSerializer(serializers.ModelSerializer):
    ship_from = AddressSerializer()
    ship_to = AddressSerializer()
    package = PackageSerializer()
    upload_session = serializers.PrimaryKeyRelatedField(
        queryset=UploadSession.objects.all()
    )

    class Meta:
        model = Shipment
        fields = [
            'upload_session',
            'ship_from',
            'ship_to',
            'package',
            'shipping_service',
            'order_number',
        ]

    def update(self, instance, validated_data):
        # Handle nested updates for ship_from, ship_to, package
        address_fields = ['ship_from', 'ship_to']
        for field in address_fields:
            nested_data = validated_data.pop(field, None)
            if nested_data:
                address_instance = getattr(instance, field)
                for attr, value in nested_data.items():
                    setattr(address_instance, attr, value)
                address_instance.save()

        package_data = validated_data.pop('package', None)
        if package_data:
            package_instance = instance.package
            for attr, value in package_data.items():
                setattr(package_instance, attr, value)
            package_instance.save()

        # Update shipment fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance