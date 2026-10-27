import base64
import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import Mock, patch

import requests
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import CustomUser
from apps.payments import services
from apps.payments.gateways.eupago import EupagoGateway
from apps.payments.models import RechargeOrder, TangasPackage, Transaction, WebhookLog


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


class PublicWebhookUrlTest(TestCase):
    def test_returns_relative_path_without_setting(self):
        with override_settings(AHHH_PUBLIC_BASE_URL=''):
            self.assertEqual(
                services.public_webhook_url(),
                reverse('payments:payment_webhook'),
            )

    def test_returns_absolute_url_with_setting_and_strips_slash(self):
        with override_settings(AHHH_PUBLIC_BASE_URL='https://www.ahhh-ibiza.com/'):
            self.assertEqual(
                services.public_webhook_url(),
                'https://www.ahhh-ibiza.com' + reverse('payments:payment_webhook'),
            )


@override_settings(
    AHHH_PAYMENT_GATEWAY='eupago',
    AHHH_PAYMENT_MODE='test',
    AHHH_EUPAGO_API_KEY='eupago-test-api-key',
    AHHH_EUPAGO_WEBHOOK_SECRET='eupago-test-webhook-secret',
    AHHH_PUBLIC_BASE_URL='https://www.ahhh-ibiza.com',
)
class EupagoGatewayTest(TestCase):
    """Fase 2 de la integracion Eupago (docs/eupago_integracion.md).

    No se golpea la red: create_checkout mockea requests.post y los webhooks
    se firman con HMAC SHA-256 igual que haria Eupago.
    """

    secret = 'eupago-test-webhook-secret'
    api_key = 'eupago-test-api-key'
    checkout_url = 'https://sandbox.eupago.pt/api/extern/paybylink/form/abc'

    def setUp(self):
        self.professional = CustomUser.objects.create_user(
            username='pro-eupago',
            password='test-password',
            email='pro-eupago@example.com',
            type=CustomUser.Types.PROFESSIONAL,
        )
        self.package = TangasPackage.objects.create(
            name='Pack Eupago',
            tangas_amount=50,
            price_eur=Decimal('15.00'),
            sort_order=1,
            is_active=True,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _eupago_response(self, **overrides):
        data = {
            'transactionStatus': 'Success',
            'transactionID': 'af3df607c6724870be962a69cac30b99',
            'status': 'Pendente',
            'redirectUrl': self.checkout_url,
        }
        data.update(overrides)
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = data
        return response

    def _create_pending_order(self):
        order = services.create_recharge_order(self.professional, self.package.pk)
        with patch(
            'apps.payments.gateways.eupago.requests.post',
            return_value=self._eupago_response(),
        ):
            services.start_checkout(order)
        order.refresh_from_db()
        return order

    def _sign(self, body, key=None):
        return base64.b64encode(
            hmac.new((key or self.secret).encode(), body, hashlib.sha256).digest()
        ).decode('ascii')

    def _webhook_request(self, body, signature=None):
        request = RequestFactory().post(
            '/pagos/webhook/', data=body, content_type='application/json',
        )
        if signature is not None:
            request.META['HTTP_X_SIGNATURE'] = signature
        return request

    def _payload(self, identifier='recharge-abc', status='Paid', amount=15.0,
                 currency='EUR'):
        transaction = {
            'identifier': identifier,
            'status': status,
            'trid': 42,
            'method': 'Multibanco',
        }
        if amount is not None:
            transaction['amount'] = {'value': float(amount), 'currency': currency}
        return {'transactions': transaction, 'channel': {'name': 'sandbox'}}

    def _post_webhook(self, order, status='Paid', amount=None, currency='EUR',
                      identifier=None, signature_key=None, sign=True):
        body = json.dumps(self._payload(
            identifier=identifier or order.gateway_order_id,
            status=status,
            currency=currency,
            amount=order.amount_eur if amount is None else amount,
        )).encode('utf-8')
        extra = {'HTTP_X_SIGNATURE': self._sign(body, key=signature_key)} if sign else {}
        return self.client.post(
            reverse('payments:payment_webhook'),
            data=body,
            content_type='application/json',
            **extra,
        )

    # ------------------------------------------------------------------
    # create_checkout
    # ------------------------------------------------------------------
    def test_create_checkout_returns_url_and_reference(self):
        order = services.create_recharge_order(self.professional, self.package.pk)
        with patch(
            'apps.payments.gateways.eupago.requests.post',
            return_value=self._eupago_response(),
        ) as post:
            result = EupagoGateway().create_checkout(order)

        self.assertEqual(result['checkout_url'], self.checkout_url)
        self.assertTrue(result['gateway_order_id'].startswith('recharge-'))

        self.assertEqual(
            post.call_args[0][0],
            'https://sandbox.eupago.pt/api/v1.02/paybylink/create',
        )
        kwargs = post.call_args[1]
        self.assertEqual(kwargs['headers'], {'Authorization': f'ApiKey {self.api_key}'})
        self.assertEqual(kwargs['timeout'], 10)

        payload = kwargs['json']
        self.assertEqual(payload['payment']['identifier'], result['gateway_order_id'])
        self.assertEqual(payload['payment']['amount'], {'value': 15.0, 'currency': 'EUR'})
        self.assertEqual(payload['payment']['lang'], 'ES')
        self.assertEqual(payload['customer'], {'notify': False})
        expected_return = 'https://www.ahhh-ibiza.com' + reverse(
            'payments:recharge_result', args=[order.pk],
        )
        for key in ('successUrl', 'failUrl', 'backUrl'):
            self.assertEqual(payload['payment'][key], expected_return)

    def test_create_checkout_live_uses_production_host(self):
        order = services.create_recharge_order(self.professional, self.package.pk)
        with override_settings(AHHH_PAYMENT_MODE='live'):
            with patch(
                'apps.payments.gateways.eupago.requests.post',
                return_value=self._eupago_response(),
            ) as post:
                EupagoGateway().create_checkout(order)
        self.assertTrue(
            post.call_args[0][0].startswith('https://clientes.eupago.pt/api/'),
            post.call_args[0][0],
        )

    def test_create_checkout_rejected_raises_value_error(self):
        order = services.create_recharge_order(self.professional, self.package.pk)
        rejected = self._eupago_response(
            transactionStatus='Rejected', code='APIKEY_MISSING', text='Chave invalida',
        )
        with patch('apps.payments.gateways.eupago.requests.post', return_value=rejected):
            with self.assertRaises(ValueError):
                EupagoGateway().create_checkout(order)

    def test_create_checkout_without_redirect_url_raises_value_error(self):
        order = services.create_recharge_order(self.professional, self.package.pk)
        broken = self._eupago_response(redirectUrl='')
        with patch('apps.payments.gateways.eupago.requests.post', return_value=broken):
            with self.assertRaises(ValueError):
                EupagoGateway().create_checkout(order)

    def test_create_checkout_network_error_raises_value_error(self):
        order = services.create_recharge_order(self.professional, self.package.pk)
        with patch(
            'apps.payments.gateways.eupago.requests.post',
            side_effect=requests.Timeout('timeout'),
        ):
            with self.assertRaises(ValueError):
                EupagoGateway().create_checkout(order)

    def test_create_checkout_without_api_key_raises_configuration_error(self):
        order = services.create_recharge_order(self.professional, self.package.pk)
        with override_settings(AHHH_EUPAGO_API_KEY=''):
            with self.assertRaises(ImproperlyConfigured):
                EupagoGateway().create_checkout(order)

    def test_start_checkout_persists_gateway_reference(self):
        order = self._create_pending_order()
        self.assertTrue(order.gateway_order_id.startswith('recharge-'))
        with patch(
            'apps.payments.gateways.eupago.requests.post',
            return_value=self._eupago_response(),
        ) as post:
            checkout_url = services.start_checkout(order)
        order.refresh_from_db()
        identifier = post.call_args[1]['json']['payment']['identifier']
        self.assertEqual(order.gateway_order_id, identifier)
        self.assertEqual(checkout_url, self.checkout_url)

    # ------------------------------------------------------------------
    # verify_webhook
    # ------------------------------------------------------------------
    def test_verify_webhook_accepts_valid_signature(self):
        body = json.dumps(self._payload()).encode('utf-8')
        request = self._webhook_request(body, signature=self._sign(body))
        self.assertTrue(EupagoGateway().verify_webhook(request))

    def test_verify_webhook_rejects_wrong_signature(self):
        body = json.dumps(self._payload()).encode('utf-8')
        request = self._webhook_request(body, signature=self._sign(body, key='otra'))
        self.assertFalse(EupagoGateway().verify_webhook(request))

    def test_verify_webhook_rejects_missing_signature(self):
        body = json.dumps(self._payload()).encode('utf-8')
        self.assertFalse(EupagoGateway().verify_webhook(self._webhook_request(body)))

    def test_verify_webhook_rejects_missing_secret(self):
        body = json.dumps(self._payload()).encode('utf-8')
        request = self._webhook_request(body, signature=self._sign(body))
        with override_settings(AHHH_EUPAGO_WEBHOOK_SECRET=''):
            self.assertFalse(EupagoGateway().verify_webhook(request))

    # ------------------------------------------------------------------
    # parse_event
    # ------------------------------------------------------------------
    def test_parse_event_paid(self):
        body = json.dumps(self._payload()).encode('utf-8')
        event = EupagoGateway().parse_event(self._webhook_request(body))
        self.assertEqual(event['event_type'], 'payment.succeeded')
        self.assertEqual(event['gateway_order_id'], 'recharge-abc')
        self.assertEqual(event['amount'], 15.0)
        self.assertEqual(event['currency'], 'EUR')
        self.assertEqual(event['raw']['transactions']['status'], 'Paid')

    def test_parse_event_failure_statuses(self):
        for status in ('Error', 'Cancel', 'Expired'):
            with self.subTest(status=status):
                body = json.dumps(self._payload(status=status)).encode('utf-8')
                event = EupagoGateway().parse_event(self._webhook_request(body))
                self.assertEqual(event['event_type'], 'payment.failed')
                self.assertEqual(event['gateway_order_id'], 'recharge-abc')

    def test_parse_event_rejects_unexpected_status(self):
        body = json.dumps(self._payload(status='Refund')).encode('utf-8')
        with self.assertRaises(ValueError):
            EupagoGateway().parse_event(self._webhook_request(body))

    def test_parse_event_rejects_missing_structure(self):
        payloads = (
            {},
            {'transactions': {}},
            {'transactions': {'identifier': 'recharge-abc', 'status': 'Paid'}},
            {'transactions': {'status': 'Paid', 'amount': {'value': 15, 'currency': 'EUR'}}},
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                body = json.dumps(payload).encode('utf-8')
                with self.assertRaises(ValueError):
                    EupagoGateway().parse_event(self._webhook_request(body))

    def test_parse_event_rejects_invalid_json(self):
        with self.assertRaises(ValueError):
            EupagoGateway().parse_event(self._webhook_request(b'no-es-json'))

    # ------------------------------------------------------------------
    # Webhook end-to-end (vista payment_webhook con la pasarela eupago)
    # ------------------------------------------------------------------
    def test_webhook_paid_credits_balance_only_once(self):
        order = self._create_pending_order()
        first = self._post_webhook(order)
        second = self._post_webhook(order)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)

        order.refresh_from_db()
        self.assertEqual(order.status, RechargeOrder.Status.PAID)
        self.assertTrue(order.gateway_order_id.startswith('recharge-'))
        self.professional.refresh_from_db()
        self.assertEqual(self.professional.tangas_balance, self.package.tangas_amount)
        self.assertEqual(Transaction.objects.filter(recharge_order=order).count(), 1)

    def test_webhook_invalid_signature_rejected(self):
        order = self._create_pending_order()
        resp = self._post_webhook(order, signature_key='clave-equivocada')
        self.assertEqual(resp.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, RechargeOrder.Status.PENDING)
        self.professional.refresh_from_db()
        self.assertEqual(self.professional.tangas_balance, Decimal('0.00'))
        self.assertTrue(
            WebhookLog.objects.filter(gateway='eupago', status='invalid_signature').exists()
        )

    def test_webhook_error_marks_order_failed(self):
        order = self._create_pending_order()
        resp = self._post_webhook(order, status='Error')
        self.assertEqual(resp.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, RechargeOrder.Status.FAILED)
        self.professional.refresh_from_db()
        self.assertEqual(self.professional.tangas_balance, Decimal('0.00'))
        self.assertFalse(Transaction.objects.filter(recharge_order=order).exists())

    def test_webhook_wrong_amount_rejected(self):
        order = self._create_pending_order()
        resp = self._post_webhook(order, amount='99.99')
        self.assertEqual(resp.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, RechargeOrder.Status.PENDING)
        self.professional.refresh_from_db()
        self.assertEqual(self.professional.tangas_balance, Decimal('0.00'))

    def test_webhook_unknown_reference_rejected(self):
        order = self._create_pending_order()
        resp = self._post_webhook(order, identifier='recharge-desconocida')
        self.assertEqual(resp.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, RechargeOrder.Status.PENDING)

    # ------------------------------------------------------------------
    # Webhook 1.0 (GET con parametros y chave_api)
    # ------------------------------------------------------------------
    def _legacy_params(self, order=None, **overrides):
        params = {
            'valor': str(order.amount_eur) if order is not None else '15.00',
            'canal': 'sandbox',
            'referencia': '102087857',
            'transacao': '10409241',
            'identificador': order.gateway_order_id if order is not None else 'recharge-abc',
            'mp': 'PC:PT',
            'chave_api': self.api_key,
            'data': '2026-10-20:12:00',
            'entidade': '82307',
            'comissao': '1.14',
            'local': 'Lisboa',
        }
        params.update(overrides)
        return params

    def _get_webhook(self, order=None, **overrides):
        return self.client.get(
            reverse('payments:payment_webhook'),
            self._legacy_params(order, **overrides),
        )

    def test_verify_webhook_legacy_accepts_configured_api_key(self):
        request = RequestFactory().get('/pagos/webhook/', self._legacy_params())
        self.assertTrue(EupagoGateway().verify_webhook(request))

    def test_verify_webhook_legacy_rejects_unknown_api_key(self):
        request = RequestFactory().get(
            '/pagos/webhook/', self._legacy_params(chave_api='0000-0000-0000-0000-0000'),
        )
        self.assertFalse(EupagoGateway().verify_webhook(request))

    def test_verify_webhook_legacy_rejects_missing_api_key(self):
        request = RequestFactory().get('/pagos/webhook/', self._legacy_params(chave_api=''))
        self.assertFalse(EupagoGateway().verify_webhook(request))

    def test_verify_webhook_legacy_rejects_when_api_key_unset(self):
        request = RequestFactory().get('/pagos/webhook/', self._legacy_params())
        with override_settings(AHHH_EUPAGO_API_KEY=''):
            self.assertFalse(EupagoGateway().verify_webhook(request))

    def test_parse_event_legacy_paid(self):
        request = RequestFactory().get('/pagos/webhook/', self._legacy_params())
        event = EupagoGateway().parse_event(request)
        self.assertEqual(event['event_type'], 'payment.succeeded')
        self.assertEqual(event['gateway_order_id'], 'recharge-abc')
        self.assertEqual(event['amount'], Decimal('15.00'))
        self.assertEqual(event['currency'], 'EUR')
        self.assertEqual(event['raw']['transacao'], '10409241')

    def test_parse_event_legacy_accepts_comma_decimal(self):
        request = RequestFactory().get(
            '/pagos/webhook/', self._legacy_params(valor='15,00'),
        )
        self.assertEqual(
            EupagoGateway().parse_event(request)['amount'], Decimal('15.00'),
        )

    def test_parse_event_legacy_rejects_missing_params(self):
        for missing in ('identificador', 'valor'):
            with self.subTest(missing=missing):
                request = RequestFactory().get(
                    '/pagos/webhook/', self._legacy_params(**{missing: ''}),
                )
                with self.assertRaises(ValueError):
                    EupagoGateway().parse_event(request)

    def test_parse_event_legacy_rejects_invalid_amount(self):
        request = RequestFactory().get(
            '/pagos/webhook/', self._legacy_params(valor='no-es-numero'),
        )
        with self.assertRaises(ValueError):
            EupagoGateway().parse_event(request)

    def test_webhook_legacy_paid_credits_balance_only_once(self):
        order = self._create_pending_order()
        first = self._get_webhook(order)
        second = self._get_webhook(order)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)

        order.refresh_from_db()
        self.assertEqual(order.status, RechargeOrder.Status.PAID)
        self.professional.refresh_from_db()
        self.assertEqual(self.professional.tangas_balance, self.package.tangas_amount)
        self.assertEqual(Transaction.objects.filter(recharge_order=order).count(), 1)
        self.assertTrue(
            WebhookLog.objects.filter(gateway='eupago', status='received').exists()
        )

    def test_webhook_legacy_invalid_api_key_rejected(self):
        order = self._create_pending_order()
        resp = self._get_webhook(order, chave_api='clave-equivocada')
        self.assertEqual(resp.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, RechargeOrder.Status.PENDING)
        self.professional.refresh_from_db()
        self.assertEqual(self.professional.tangas_balance, Decimal('0.00'))
        self.assertTrue(
            WebhookLog.objects.filter(gateway='eupago', status='invalid_signature').exists()
        )

    def test_webhook_legacy_wrong_amount_rejected(self):
        order = self._create_pending_order()
        resp = self._get_webhook(order, valor='99.99')
        self.assertEqual(resp.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, RechargeOrder.Status.PENDING)
        self.professional.refresh_from_db()
        self.assertEqual(self.professional.tangas_balance, Decimal('0.00'))

    def test_webhook_legacy_missing_amount_rejected(self):
        order = self._create_pending_order()
        resp = self._get_webhook(order, valor='')
        self.assertEqual(resp.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, RechargeOrder.Status.PENDING)
        self.professional.refresh_from_db()
        self.assertEqual(self.professional.tangas_balance, Decimal('0.00'))

    def test_webhook_legacy_unknown_reference_rejected(self):
        order = self._create_pending_order()
        resp = self._get_webhook(order, identificador='recharge-desconocida')
        self.assertEqual(resp.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, RechargeOrder.Status.PENDING)
