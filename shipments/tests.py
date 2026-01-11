from django.test import TestCase
from rest_framework.test import APIClient

from .models import Address, Package, UploadSession, Shipment
from .services.bulk_ops import update_ship_from


class BulkAddressCloneTests(TestCase):
    def setUp(self):
        self.from_addr = Address.objects.create(name='From', address_line1='1 A St', city='City', postal_code='11111')
        self.to_addr = Address.objects.create(name='To', address_line1='2 B St', city='Town', postal_code='22222')
        self.pkg = Package.objects.create(weight_lbs=1, weight_oz=0)
        self.session = UploadSession.objects.create()
        # both shipments share same from_addr
        self.s1 = Shipment.objects.create(upload_session=self.session, ship_from=self.from_addr, ship_to=self.to_addr, package=self.pkg)
        self.s2 = Shipment.objects.create(upload_session=self.session, ship_from=self.from_addr, ship_to=self.to_addr, package=self.pkg)

    def test_update_ship_from_partial_clones_address_for_single_shipment(self):
        original_id = self.from_addr.id
        res = update_ship_from([self.s1.pk], {'city': 'NewCity'})
        self.assertIn(self.s1.pk, res['updated'])
        self.s1.refresh_from_db()
        self.s2.refresh_from_db()
        # s1 should have a new address with updated city
        self.assertEqual(self.s1.ship_from.city, 'NewCity')
        self.assertNotEqual(self.s1.ship_from.id, original_id)
        # s2 should still reference the original address unchanged
        self.assertEqual(self.s2.ship_from.id, original_id)
        self.from_addr.refresh_from_db()
        self.assertEqual(self.from_addr.city, 'City')


class ShipmentSerializerCloneAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.from_addr = Address.objects.create(name='From', address_line1='1 A St', city='City', postal_code='11111')
        self.to_addr = Address.objects.create(name='To', address_line1='2 B St', city='Town', postal_code='22222')
        self.pkg = Package.objects.create(weight_lbs=1, weight_oz=0)
        self.session = UploadSession.objects.create()
        self.s1 = Shipment.objects.create(upload_session=self.session, ship_from=self.from_addr, ship_to=self.to_addr, package=self.pkg)
        self.s2 = Shipment.objects.create(upload_session=self.session, ship_from=self.from_addr, ship_to=self.to_addr, package=self.pkg)

    def test_patch_shipment_clones_ship_from(self):
        url = f'/api/shipments/shipments/{self.s1.pk}/'
        payload = {'ship_from': {'city': 'PatchedCity'}}
        resp = self.client.patch(url, payload, format='json')
        self.assertEqual(resp.status_code, 200)
        self.s1.refresh_from_db()
        self.s2.refresh_from_db()
        # s1 should have new address, s2 should remain pointing at original
        self.assertEqual(self.s1.ship_from.city, 'PatchedCity')
        self.assertNotEqual(self.s1.ship_from.id, self.from_addr.id)
        self.assertEqual(self.s2.ship_from.id, self.from_addr.id)
