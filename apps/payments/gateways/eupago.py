import base64
import hashlib
import hmac
import json
import logging
from decimal import Decimal, InvalidOperation
from uuid import uuid4

import requests
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse

from .base import BaseGateway

logger = logging.getLogger(__name__)

_BASE_URLS = {
    'test': 'https://sandbox.eupago.pt/api/',
    'live': 'https://clientes.eupago.pt/api/',
}

_STATUS_EVENTS = {
    'Paid': 'payment.succeeded',
    'Error': 'payment.failed',
    'Cancel': 'payment.failed',
    'Expired': 'payment.failed',
}

_TIMEOUT_SECONDS = 10


def _absolute_url(path):
    """Convierte una ruta local en URL absoluta usando AHHH_PUBLIC_BASE_URL."""
    base = getattr(settings, 'AHHH_PUBLIC_BASE_URL', '').rstrip('/')
    return f'{base}{path}' if base else path


class EupagoGateway(BaseGateway):
    """Pasarela Eupago (eupago.pt) integrada via Pay By Link.

    Crea una pagina hosted de Eupago (`/v1.02/paybylink/create`) que devuelve
    una `checkout_url`; el usuario paga ahi (Multibanco, MB WAY, tarjeta) y
    Eupago notifica a `/pagos/webhook/`.

    Soporta los dos formatos de notificacion de Eupago:

    * Webhook 2.0: POST JSON con firma HMAC SHA-256 (base64) en `X-Signature`,
      calculada sobre el body con AHHH_EUPAGO_WEBHOOK_SECRET. Informa de
      pagos, errores, cancelaciones y expiraciones.
    * Webhook 1.0 (respaldo): GET con parametros en la URL (`identificador`,
      `valor`, `chave_api`...). No necesita secreto aparte: se valida que
      `chave_api` sea AHHH_EUPAGO_API_KEY. Solo notifica pagos realizados.

    Configuracion (ver docs/eupago_integracion.md):
        AHHH_EUPAGO_API_KEY        clave de API del backoffice de Eupago
        AHHH_EUPAGO_WEBHOOK_SECRET secreto de firma del webhook 2.0
        AHHH_PAYMENT_MODE          'test' => sandbox, 'live' => produccion

    La referencia que viaja de ida y vuelta es `payment.identifier`
    (f'recharge-<hex>'): se guarda en RechargeOrder.gateway_order_id y Eupago
    la devuelve en `transactions.identifier` (2.0) o `identificador` (1.0).
    """

    name = 'eupago'

    def create_checkout(self, order):
        api_key = getattr(settings, 'AHHH_EUPAGO_API_KEY', '')
        if not api_key:
            raise ImproperlyConfigured(
                'Falta AHHH_EUPAGO_API_KEY para usar la pasarela eupago.'
            )

        mode = getattr(settings, 'AHHH_PAYMENT_MODE', 'test')
        base_url = _BASE_URLS.get(mode, _BASE_URLS['test'])
        identifier = f'recharge-{uuid4().hex}'
        return_url = _absolute_url(
            reverse('payments:recharge_result', args=[order.id])
        )

        payload = {
            'payment': {
                'identifier': identifier,
                'amount': {
                    'value': float(order.amount_eur),
                    'currency': order.currency,
                },
                'successUrl': return_url,
                'failUrl': return_url,
                'backUrl': return_url,
                'lang': 'ES',
            },
            'customer': {'notify': False},
        }

        try:
            response = requests.post(
                f'{base_url}v1.02/paybylink/create',
                json=payload,
                headers={'Authorization': f'ApiKey {api_key}'},
                timeout=_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.exception('Eupago inaccesible al crear checkout de la orden %s', order.id)
            raise ValueError(
                'No se pudo contactar con la pasarela de pago. Inténtalo de nuevo.'
            ) from exc

        if data.get('transactionStatus') != 'Success':
            logger.error(
                'Eupago rechazó el checkout de la orden %s: %s %s',
                order.id, data.get('code'), data.get('text'),
            )
            raise ValueError(
                'No se pudo iniciar el pago. Inténtalo de nuevo más tarde.'
            )

        checkout_url = data.get('redirectUrl')
        if not checkout_url:
            logger.error('Eupago devolvió Success sin redirectUrl (orden %s)', order.id)
            raise ValueError(
                'No se pudo iniciar el pago. Inténtalo de nuevo más tarde.'
            )

        logger.info(
            'Checkout Eupago creado para la orden %s: transactionID=%s',
            order.id, data.get('transactionID'),
        )
        return {'checkout_url': checkout_url, 'gateway_order_id': identifier}

    def verify_webhook(self, request):
        if request.method == 'GET':
            return self._verify_legacy(request)
        return self._verify_signature(request)

    def _verify_legacy(self, request):
        """Webhook 1.0: GET con la API key del canal en `chave_api`."""
        api_key = getattr(settings, 'AHHH_EUPAGO_API_KEY', '')
        received = request.GET.get('chave_api', '')
        if not api_key or not received:
            return False
        return hmac.compare_digest(api_key.encode(), received.encode())

    def _verify_signature(self, request):
        secret = getattr(settings, 'AHHH_EUPAGO_WEBHOOK_SECRET', '')
        signature = request.headers.get('X-Signature', '')
        if not secret or not signature:
            return False
        expected = base64.b64encode(
            hmac.new(secret.encode(), request.body, hashlib.sha256).digest()
        )
        return hmac.compare_digest(expected, signature.encode())

    def parse_event(self, request):
        if request.method == 'GET':
            return self._parse_legacy_event(request)
        return self._parse_json_event(request)

    def _parse_legacy_event(self, request):
        params = request.GET
        identifier = params.get('identificador', '').strip()
        amount_value = params.get('valor', '').strip()
        if not identifier or not amount_value:
            raise ValueError(
                'Webhook 1.0 de Eupago sin "identificador" o "valor".'
            )
        try:
            amount = Decimal(amount_value.replace(',', '.'))
        except InvalidOperation as exc:
            raise ValueError(
                f'Webhook 1.0 de Eupago con importe no válido: {amount_value!r}.'
            ) from exc

        logger.info(
            'Webhook Eupago 1.0 Paid (orden externa %s, transacao=%s, método=%s)',
            identifier, params.get('transacao'), params.get('mp'),
        )
        return {
            'event_type': 'payment.succeeded',
            'gateway_order_id': identifier,
            'amount': amount,
            'currency': 'EUR',
            'raw': params.dict(),
        }

    def _parse_json_event(self, request):
        try:
            body = json.loads(request.body)
        except ValueError as exc:
            raise ValueError('Webhook de Eupago sin JSON válido.') from exc

        transactions = body.get('transactions')
        if not isinstance(transactions, dict):
            raise ValueError('Webhook de Eupago sin bloque "transactions".')

        identifier = transactions.get('identifier')
        status = transactions.get('status')
        if not identifier or status not in _STATUS_EVENTS:
            raise ValueError(
                f'Webhook de Eupago con estructura inesperada: status={status!r}.'
            )

        amount = transactions.get('amount')
        amount_value = amount.get('value') if isinstance(amount, dict) else None
        amount_currency = amount.get('currency') if isinstance(amount, dict) else None

        event_type = _STATUS_EVENTS[status]
        if event_type == 'payment.succeeded' and (amount_value is None or not amount_currency):
            raise ValueError('Webhook de Eupago "Paid" sin importe o moneda.')

        logger.info(
            'Webhook Eupago %s (orden externa %s, trid=%s, método=%s)',
            status, identifier, transactions.get('trid'), transactions.get('method'),
        )
        return {
            'event_type': event_type,
            'gateway_order_id': identifier,
            'amount': amount_value,
            'currency': amount_currency,
            'raw': body,
        }
