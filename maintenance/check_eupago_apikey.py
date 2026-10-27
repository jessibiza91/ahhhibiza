"""Comprueba la API Key de Eupago contra sandbox y/o produccion.

Uso (desde la raiz del proyecto):
    venv\\Scripts\\python.exe maintenance\\check_eupago_apikey.py          # sandbox
    venv\\Scripts\\python.exe maintenance\\check_eupago_apikey.py --prod   # produccion
    venv\\Scripts\\python.exe maintenance\\check_eupago_apikey.py --both   # ambas

Lee AHHH_EUPAGO_API_KEY del .env (nunca la imprime completa). Cada comprobacion
crea un Pay By Link de 1 EUR que nadie paga: en sandbox es ficticio y en
produccion caduca solo en 24 h. Las claves de produccion no funcionan en
sandbox y viceversa: cada entorno tiene su propia key.
"""

import argparse
import os
import sys
from pathlib import Path
from uuid import uuid4

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
ENDPOINTS = {
    'sandbox': 'https://sandbox.eupago.pt/api/v1.02/paybylink/create',
    'prod': 'https://clientes.eupago.pt/api/v1.02/paybylink/create',
}


def load_api_key():
    load_dotenv(ROOT / '.env')
    return os.getenv('AHHH_EUPAGO_API_KEY', '').strip()


def check(name, url, api_key):
    print(f'--- {name} ---')
    print(f'POST {url}')
    try:
        response = requests.post(
            url,
            json={
                'payment': {
                    'identifier': f'check-apikey-{uuid4().hex}',
                    'amount': {'value': 1.0, 'currency': 'EUR'},
                    'lang': 'ES',
                },
                'customer': {'notify': False},
            },
            headers={'Authorization': f'ApiKey {api_key}'},
            timeout=15,
        )
    except requests.RequestException as exc:
        print(f'ERROR DE RED: {exc}')
        return False

    try:
        data = response.json()
    except ValueError:
        print(f'HTTP {response.status_code} | respuesta no JSON: {response.text[:300]}')
        return False

    status = data.get('transactionStatus')
    detail = ' '.join(
        str(part) for part in (data.get('code'), data.get('text')) if part
    )
    print(f"HTTP {response.status_code} | {status} {detail}".rstrip())

    if status == 'Success':
        print(f'OK: la key funciona en {name}.')
        print(f"Link de prueba (no pagar): {data.get('redirectUrl')}")
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description='Comprueba AHHH_EUPAGO_API_KEY.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--prod', action='store_true', help='comprueba solo produccion')
    group.add_argument('--both', action='store_true', help='comprueba sandbox y produccion')
    args = parser.parse_args()

    api_key = load_api_key()
    if not api_key:
        print('FALTA AHHH_EUPAGO_API_KEY en el .env')
        return 1

    print(f'API key: {api_key[:4]}...{api_key[-4:]} ({len(api_key)} chars)')
    if args.prod:
        targets = ['prod']
    elif args.both:
        targets = ['sandbox', 'prod']
    else:
        targets = ['sandbox']

    results = [check(name, ENDPOINTS[name], api_key) for name in targets]
    return 0 if all(results) else 2


if __name__ == '__main__':
    sys.exit(main())
