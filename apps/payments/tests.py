from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import CustomUser
from apps.payments.models import RechargeOrder, TangasPackage


class ControlTangasPackagesTest(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username='admin', email='admin@test.com', password='pass',
            is_staff=True, is_superuser=True,
        )
        self.client.force_login(self.admin)

    def test_list_packages(self):
        TangasPackage.objects.create(name='Pack Test', tangas_amount=25, price_eur=8)
        resp = self.client.get(reverse('payments:control_tangas_packages'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Pack Test')

    def test_create_package(self):
        resp = self.client.post(reverse('payments:control_tangas_package_create'), {
            'name': 'Pack Nuevo',
            'tangas_amount': '50',
            'price_eur': '15.00',
            'sort_order': '1',
            'is_active': 'on',
        })
        self.assertEqual(resp.status_code, 200)
        package = TangasPackage.objects.get(name='Pack Nuevo')
        self.assertEqual(package.tangas_amount, 50)
        self.assertEqual(str(package.price_eur), '15.00')

    def test_invalid_amount_rejected(self):
        resp = self.client.post(reverse('payments:control_tangas_package_create'), {
            'name': 'Pack Malo',
            'tangas_amount': '0',
            'price_eur': '15.00',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'mayor que cero')
        self.assertFalse(TangasPackage.objects.filter(name='Pack Malo').exists())

    def test_edit_package(self):
        pkg = TangasPackage.objects.create(name='Pack Edit', tangas_amount=10, price_eur=5)
        resp = self.client.post(reverse('payments:control_tangas_package_edit', args=[pkg.pk]), {
            'name': 'Pack Edit',
            'tangas_amount': '99',
            'price_eur': '12.50',
            'sort_order': '2',
        })
        self.assertEqual(resp.status_code, 200)
        pkg.refresh_from_db()
        self.assertEqual(pkg.tangas_amount, 99)

    def test_delete_without_orders(self):
        pkg = TangasPackage.objects.create(name='Pack Del', tangas_amount=10, price_eur=5)
        resp = self.client.post(reverse('payments:control_tangas_package_delete', args=[pkg.pk]))
        self.assertRedirects(resp, reverse('payments:control_tangas_packages'))
        self.assertFalse(TangasPackage.objects.filter(pk=pkg.pk).exists())

    def test_delete_with_orders_deactivates(self):
        pkg = TangasPackage.objects.create(name='Pack Con Compras', tangas_amount=10, price_eur=5)
        user = CustomUser.objects.create_user(username='pro', email='pro@test.com', password='pass')
        RechargeOrder.objects.create(
            user=user, package=pkg, tangas_amount=10, amount_eur=5,
            currency='EUR', status=RechargeOrder.Status.PENDING,
        )
        resp = self.client.post(reverse('payments:control_tangas_package_delete', args=[pkg.pk]))
        self.assertRedirects(resp, reverse('payments:control_tangas_packages'))
        pkg.refresh_from_db()
        self.assertFalse(pkg.is_active)

    def test_requires_staff(self):
        self.client.force_login(CustomUser.objects.create_user(username='nope', email='nope@test.com', password='pass'))
        resp = self.client.get(reverse('payments:control_tangas_packages'))
        self.assertEqual(resp.status_code, 302)
