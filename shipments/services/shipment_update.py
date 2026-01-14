def assign_shipping_service_option(shipment, service, option=None):
    """
    Assign shipping service and option to a shipment.
    """
    shipment.shipping_service = service
    if option is not None:
        shipment.shipping_option = option
    shipment.save()
    
def update_shipment(shipment_id: int, data: dict) -> dict:
    """
    Update shipment fields, re-validate, re-price, and persist changes.
    Supports updating shipping_service, shipping_option, and other editable fields.
    """
    from shipments.models import Shipment
    from shipments.services.bulk_ops import calculate_step4review_price
    try:
        shipment = Shipment.objects.select_related('package').get(pk=shipment_id)
    except Shipment.DoesNotExist:
        return {'shipment_id': shipment_id, 'updated': False, 'error': 'Shipment not found'}

    # Update allowed fields
    allowed_fields = ['shipping_service', 'shipping_option', 'order_number']
    for field in allowed_fields:
        if field in data:
            setattr(shipment, field, data[field])

    # Recalculate price if shipping_service or shipping_option changed
    service = data.get('shipping_service', shipment.shipping_service)
    option = data.get('shipping_option', shipment.shipping_option or 'priority')
    price = calculate_step4review_price(service, option)
    shipment.price_cents = int(price * 100)

    shipment.save()
    return {
        'shipment_id': shipment_id,
        'updated': True,
        'shipping_service': shipment.shipping_service,
        'shipping_option': shipment.shipping_option,
        'price_cents': shipment.price_cents,
    }
