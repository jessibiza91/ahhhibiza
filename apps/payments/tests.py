from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import CustomUser
from apps.payments import services
from apps.payments.models import RechargeOrder, TangasPackage, Transaction


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


class RechargeFlowTest(TestCase):
    def setUp(self):
        self.professional = CustomUser.objects.create_user(
            username='pro',
            password='test-password',
            email='pro@example.com',
            type=CustomUser.Types.PROFESSIONAL,
        )
        self.package = TangasPackage.objects.create(
            name='Pack Test',
            tangas_amount=50,
            price_eur=Decimal('15.00'),
            sort_order=1,
            is_active=True,
        )

    def _create_pending_order(self):
        order = services.create_recharge_order(self.professional, self.package.pk)
        services.start_checkout(order)
        order.refresh_from_db()
        return order

    def _post_webhook(self, order, event_type='payment.succeeded', amount=None, currency='EUR'):
        self.client.force_login(self.professional)
        return self.client.post(reverse('payments:payment_webhook'), {
            'event_type': event_type,
            'gateway_order_id': order.gateway_order_id,
            'amount': amount if amount is not None else order.amount_eur,
            'currency': currency,
        })

    def test_recharge_start_requires_login(self):
        resp = self.client.post(reverse('payments:recharge_start'), {'package_id': self.package.pk})
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp.url)
        self.assertFalse(RechargeOrder.objects.exists())

    def test_recharge_start_rejects_client_role(self):
        client = CustomUser.objects.create_user(
            username='client', password='test-password', email='client@example.com',
            type=CustomUser.Types.CLIENT,
        )
        self.client.force_login(client)
        resp = self.client.post(reverse('payments:recharge_start'), {'package_id': self.package.pk})
        self.assertRedirects(resp, reverse('user_dispatch'), fetch_redirect_response=False)
        self.assertFalse(RechargeOrder.objects.exists())

    def test_recharge_start_as_professional_creates_pending_order(self):
        self.client.force_login(self.professional)
        resp = self.client.post(reverse('payments:recharge_start'), {'package_id': self.package.pk})
        order = RechargeOrder.objects.get(user=self.professional)
        self.assertEqual(order.status, RechargeOrder.Status.PENDING)
        self.assertEqual(order.tangas_amount, 50)
        self.assertEqual(order.amount_eur, self.package.price_eur)
        self.assertRedirects(resp, reverse('payments:dummy_checkout', args=[order.pk]))

    def test_create_recharge_order_uses_server_side_amounts(self):
        order = services.create_recharge_order(self.professional, self.package.pk)
        self.assertEqual(order.status, RechargeOrder.Status.PENDING)
        self.assertEqual(order.tangas_amount, self.package.tangas_amount)
        self.assertEqual(order.amount_eur, self.package.price_eur)
        self.assertEqual(order.currency, 'EUR')

    def test_confirm_payment_rejects_cancelled_order(self):
        order = self._create_pending_order()
        order.status = RechargeOrder.Status.CANCELLED
        order.save(update_fields=['status'])
        with self.assertRaises(ValueError):
            services.confirm_payment(order, paid_amount=order.amount_eur, paid_currency='EUR')

    def test_confirm_payment_rejects_amount_mismatch(self):
        order = self._create_pending_order()
        with self.assertRaises(ValueError):
            services.confirm_payment(order, paid_amount='99.99', paid_currency='EUR')
        order.refresh_from_db()
        self.assertEqual(order.status, RechargeOrder.Status.PENDING)
        self.professional.refresh_from_db()
        self.assertEqual(self.professional.tangas_balance, Decimal('0.00'))

    def test_confirm_payment_credits_balance_and_transaction(self):
        order = self._create_pending_order()
        updated, credited = services.confirm_payment(
            order, paid_amount=order.amount_eur, paid_currency='EUR'
        )
        self.assertTrue(credited)
        self.assertEqual(updated.status, RechargeOrder.Status.PAID)
        self.professional.refresh_from_db()
        self.assertEqual(self.professional.tangas_balance, self.package.tangas_amount)
        tx = Transaction.objects.get(recharge_order=order)
        self.assertEqual(tx.amount, self.package.tangas_amount)
        self.assertEqual(tx.user, self.professional)

    def test_confirm_payment_is_idempotent(self):
        order = self._create_pending_order()
        _, credited_first = services.confirm_payment(
            order, paid_amount=order.amount_eur, paid_currency='EUR'
        )
        updated, credited_second = services.confirm_payment(
            order, paid_amount=order.amount_eur, paid_currency='EUR'
        )
        self.assertTrue(credited_first)
        self.assertFalse(credited_second)
        self.assertEqual(updated.status, RechargeOrder.Status.PAID)
        self.professional.refresh_from_db()
        self.assertEqual(self.professional.tangas_balance, self.package.tangas_amount)
        self.assertEqual(Transaction.objects.filter(recharge_order=order).count(), 1)

    def test_webhook_success_credits_balance(self):
        order = self._create_pending_order()
        resp = self._post_webhook(order)
        self.assertRedirects(resp, reverse('payments:recharge_result', args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual(order.status, RechargeOrder.Status.PAID)
        self.professional.refresh_from_db()
        self.assertEqual(self.professional.tangas_balance, self.package.tangas_amount)
        self.assertTrue(Transaction.objects.filter(recharge_order=order).exists())

    def test_webhook_success_accepts_localized_amount(self):
        order = self._create_pending_order()
        resp = self._post_webhook(order, amount='15,00')
        self.assertRedirects(resp, reverse('payments:recharge_result', args=[order.pk]))
        self.professional.refresh_from_db()
        self.assertEqual(self.professional.tangas_balance, self.package.tangas_amount)

    def test_webhook_is_idempotent(self):
        order = self._create_pending_order()
        self._post_webhook(order)
        self._post_webhook(order)
        self.professional.refresh_from_db()
        self.assertEqual(self.professional.tangas_balance, self.package.tangas_amount)
        self.assertEqual(Transaction.objects.filter(recharge_order=order).count(), 1)

    def test_webhook_wrong_amount_rejected(self):
        order = self._create_pending_order()
        resp = self._post_webhook(order, amount='99.99')
        self.assertEqual(resp.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, RechargeOrder.Status.PENDING)
        self.professional.refresh_from_db()
        self.assertEqual(self.professional.tangas_balance, Decimal('0.00'))
        self.assertFalse(Transaction.objects.filter(recharge_order=order).exists())

    def test_webhook_failure_does_not_credit(self):
        order = self._create_pending_order()
        resp = self._post_webhook(order, event_type='payment.failed')
        self.assertRedirects(resp, reverse('payments:recharge_result', args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual(order.status, RechargeOrder.Status.FAILED)
        self.professional.refresh_from_db()
        self.assertEqual(self.professional.tangas_balance, Decimal('0.00'))
        self.assertFalse(Transaction.objects.filter(recharge_order=order).exists())
