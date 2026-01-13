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

    # Only shape/structure validation. No business logic or nested creation.
    pass