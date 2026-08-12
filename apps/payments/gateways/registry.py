from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .base import BaseGateway
from .dummy import DummyGateway


_GATEWAYS = {
    'dummy': DummyGateway,
}


def dummy_gateway_allowed() -> bool:
    """'dummy' solo es segura en desarrollo o durante la suite de tests.

    En produccion (DEBUG=False) confirmaria pagos sin cobrar nada, por lo
    que queda bloqueada por el registry y por el system check payments.E001.
    """
    return settings.DEBUG or getattr(settings, 'TESTING', False)


def get_active_gateway() -> BaseGateway:
    """Devuelve una instancia de la pasarela configurada.

    Para añadir una pasarela nueva: crear una subclase de BaseGateway,
    registrarla en _GATEWAYS y elegirla con AHHH_PAYMENT_GATEWAY en el .env.
    """
    name = getattr(settings, 'AHHH_PAYMENT_GATEWAY', 'dummy')
    if name == 'dummy' and not dummy_gateway_allowed():
        raise ImproperlyConfigured(
            'La pasarela "dummy" no puede usarse con AHHH_DEBUG=False. '
            'Elige una pasarela real en AHHH_PAYMENT_GATEWAY.'
        )
    gateway_cls = _GATEWAYS.get(name)
    if gateway_cls is None:
        raise ImproperlyConfigured(
            f'Pasarela de pago desconocida: {name!r}. '
            f'Disponibles: {", ".join(sorted(_GATEWAYS))}.'
        )
    return gateway_cls()
