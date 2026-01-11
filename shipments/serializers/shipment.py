from __future__ import annotations
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ..models import Shipment, UploadSession, Address
from .address import AddressSerializer
from .package import PackageSerializer


class ShipmentSerializer(serializers.ModelSerializer):
    ship_from = AddressSerializer()
    ship_to = AddressSerializer()
    package = PackageSerializer()
    upload_session = serializers.PrimaryKeyRelatedField(
        queryset=UploadSession.objects.all()
    )

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
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def _save_nested(self, serializer_cls, data, partial=False):
        Model = serializer_cls.Meta.model
        if 'id' in data:
            try:
                instance = Model.objects.get(pk=data['id'])
            except Model.DoesNotExist:
                raise ValidationError({ 'id': f'{Model.__name__} with id {data["id"]} not found.' })
            serializer = serializer_cls(instance, data=data, partial=partial, context=self.context)
        else:
            serializer = serializer_cls(data=data, context=self.context)
        serializer.is_valid(raise_exception=True)
        return serializer.save()

    def create(self, validated_data):
        ship_from_data = validated_data.pop('ship_from')
        ship_to_data = validated_data.pop('ship_to')
        package_data = validated_data.pop('package')

        ship_from = self._save_nested(AddressSerializer, ship_from_data, partial=False)
        ship_to = self._save_nested(AddressSerializer, ship_to_data, partial=False)
        package = self._save_nested(PackageSerializer, package_data, partial=False)

        shipment = Shipment.objects.create(
            ship_from=ship_from,
            ship_to=ship_to,
            package=package,
            **validated_data
        )
        return shipment

    def _clone_address(self, base_instance, data: dict) -> any:
        """Create a new Address by merging base_instance fields with provided data."""
        # If payload is only id, assign that address
        AddressModel = Address
        if 'id' in data and len(data.keys()) == 1:
            try:
                return AddressModel.objects.get(pk=data['id'])
            except AddressModel.DoesNotExist:
                raise ValidationError({'id': f'Address with id {data["id"]} not found.'})

        # If id provided with other fields, use that as base
        if 'id' in data:
            try:
                base_instance = AddressModel.objects.get(pk=data['id'])
            except AddressModel.DoesNotExist:
                raise ValidationError({'id': f'Address with id {data["id"]} not found.'})

        base = {
            'name': base_instance.name,
            'address_line1': base_instance.address_line1,
            'address_line2': base_instance.address_line2,
            'city': base_instance.city,
            'state': base_instance.state,
            'postal_code': base_instance.postal_code,
            'phone': base_instance.phone,
        }
        merged = {**base, **{k: v for k, v in data.items() if k != 'id'}}
        serializer = AddressSerializer(data=merged, context=self.context)
        serializer.is_valid(raise_exception=True)
        return serializer.save()

    def update(self, instance, validated_data):
        # Nested partial updates are allowed (review/edit step)
        if 'ship_from' in validated_data:
            ship_from_data = validated_data.pop('ship_from')
            instance.ship_from = self._clone_address(instance.ship_from, ship_from_data)
        if 'ship_to' in validated_data:
            ship_to_data = validated_data.pop('ship_to')
            instance.ship_to = self._clone_address(instance.ship_to, ship_to_data)
        if 'package' in validated_data:
            instance.package = self._save_nested(PackageSerializer, validated_data.pop('package'), partial=True)

        # Update remaining scalar fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance