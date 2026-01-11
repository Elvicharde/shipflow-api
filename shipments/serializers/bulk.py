from __future__ import annotations
from rest_framework import serializers

from .address import AddressSerializer
from .package import PackageSerializer


class BulkIdsSerializer(serializers.Serializer):
    shipment_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), allow_empty=False
    )


class BulkUpdateShipFromSerializer(BulkIdsSerializer):
    address = AddressSerializer(required=True)


class BulkUpdatePackageSerializer(BulkIdsSerializer):
    package = PackageSerializer(required=True)


class BulkUpdateServiceSerializer(BulkIdsSerializer):
    shipping_service = serializers.CharField(required=True, allow_blank=False)


class BulkDeleteSerializer(BulkIdsSerializer):
    pass