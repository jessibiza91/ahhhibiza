"""Envia un webhook de prueba (1.0 o 2.0) al endpoint de pagos.

Sirve para probar el endpoint sin que Eupago llame de verdad. Antes hay que
tener una RechargeOrder PENDING cuyo `gateway_order_id` sea el `--identifier`
(ver docs/eupago_integracion.md, fase 3).

Uso:
    venv\\Scripts\\python.exe maintenance\\send_test_webhook.py \\
        --identifier recharge-abc --amount 15.00

    venv\\Scripts\\python.exe maintenance\\send_test_webhook.py \\
        --version 1.0 --identifier recharge-abc --amount 15.00

    venv\\Scripts\\python.exe maintenance\\send_test_webhook.py \\
        --url https://<tunel>/pagos/webhook/ --identifier recharge-abc --amount 15.00

Lee AHHH_EUPAGO_API_KEY (1.0) y AHHH_EUPAGO_WEBHOOK_SECRET (2.0) del .env;
se pueden sobreescribir con --api-key / --secret.
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_URL = 'http://127.0.0.1:8000/pagos/webhook/'


def legacy_params(identifier, amount, api_key):
    return {
        'valor': f'{amount:.2f}',
        'canal': 'sandbox',
        'referencia': str(random.randint(100000000, 999999999)),
        'transacao': str(random.randint(10000000, 99999999)),
        'identificador': identifier,
        'mp': 'PC:PT',
        'chave_api': api_key,
        'data': datetime.now().strftime('%Y-%m-%d:%H:%M'),
        'entidade': '82307',
        'comissao': '0.00',
        'local': 'Teste',
    }


def v2_payload(identifier, amount, status):
    return {
        'transactions': {
            'entity': 82307,
            'reference': random.randint(100000000, 999999999),
            'identifier': identifier,
            'method': 'Multibanco',
            'amount': {'value': float(amount), 'currency': 'EUR'},
            'fees': {'value': 0.0, 'currency': 'EUR'},
            'date': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'trid': random.randint(10000000, 99999999),
            'status': status,
        },
        'channel': {'name': 'sandbox'},
    }


def sign(body, secret):
    return base64.b64encode(
        hmac.new(secret.encode(), body, hashlib.sha256).digest()
    ).decode('ascii')


def main():
    parser = argparse.ArgumentParser(description='Envia un webhook de prueba.')
    parser.add_argument('--version', choices=('1.0', '2.0'), default='2.0')
    parser.add_argument('--identifier', required=True, help='gateway_order_id de la orden')
    parser.add_argument('--amount', required=True, type=float, help='importe en EUR')
    parser.add_argument('--status', default='Paid', help='2.0: Paid/Error/Cancel/Expired')
    parser.add_argument('--url', default=DEFAULT_URL)
    parser.add_argument('--api-key', default=None)
    parser.add_argument('--secret', default=None)
    args = parser.parse_args()

    load_dotenv(ROOT / '.env')
    api_key = args.api_key or os.getenv('AHHH_EUPAGO_API_KEY', '').strip()
    secret = args.secret or os.getenv('AHHH_EUPAGO_WEBHOOK_SECRET', '').strip()

    print(f'POST/GET {args.url} (webhook {args.version})')
    print(f'identifier={args.identifier} amount={args.amount:.2f}')

    if args.version == '1.0':
        if not api_key:
            print('FALTA AHHH_EUPAGO_API_KEY (o --api-key).')
            return 1
        params = legacy_params(args.identifier, args.amount, api_key)
        response = requests.get(args.url, params=params, timeout=15)
    else:
        if not secret:
            print('FALTA AHHH_EUPAGO_WEBHOOK_SECRET (o --secret).')
            return 1
        body = json.dumps(v2_payload(args.identifier, args.amount, args.status)).encode()
        response = requests.post(
            args.url,
            data=body,
            headers={
                'Content-Type': 'application/json',
                'X-Signature': sign(body, secret),
            },
            timeout=15,
        )

    print(f'HTTP {response.status_code} | {response.text[:300]}')
    return 0 if response.status_code == 200 else 2


if __name__ == '__main__':
    sys.exit(main())
