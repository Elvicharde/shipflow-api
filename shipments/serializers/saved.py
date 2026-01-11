from __future__ import annotations
from rest_framework import serializers

from ..models import SavedAddress, SavedPackage, Address, Package
from .address import AddressSerializer
from .package import PackageSerializer


class SavedAddressSerializer(serializers.ModelSerializer):
    """
    Serializer for SavedAddress:
    - address: nested read-only representation
    - address_id: write-only FK for create/update
    """
    address = AddressSerializer(read_only=True)
    address_id = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.all(), write_only=True, required=True
    )

    class Meta:
        model = SavedAddress
        fields = [
            'id',
            'label',
            'address',
            'address_id',
            'is_default',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'address']

    def create(self, validated_data):
        address = validated_data.pop('address_id')
        return SavedAddress.objects.create(address=address, **validated_data)

    def update(self, instance, validated_data):
        if 'address_id' in validated_data:
            instance.address = validated_data.pop('address_id')
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class SavedPackageSerializer(serializers.ModelSerializer):
    """
    Serializer for SavedPackage:
    - package: nested read-only representation
    - package_id: write-only FK for create/update
    """
    package = PackageSerializer(read_only=True)
    package_id = serializers.PrimaryKeyRelatedField(
        queryset=Package.objects.all(), write_only=True, required=True
    )

    class Meta:
        model = SavedPackage
        fields = [
            'id',
            'label',
            'package',
            'package_id',
            'is_default',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'package']

    def create(self, validated_data):
        package = validated_data.pop('package_id')
        return SavedPackage.objects.create(package=package, **validated_data)

    def update(self, instance, validated_data):
        if 'package_id' in validated_data:
            instance.package = validated_data.pop('package_id')
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance