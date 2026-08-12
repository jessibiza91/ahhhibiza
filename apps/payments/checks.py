from django.conf import settings
from django.core.checks import Error, register

from apps.payments.gateways.registry import dummy_gateway_allowed


@register()
def dummy_gateway_forbidden_in_production(app_configs, **kwargs):
    """Impide arrancar en produccion con la pasarela simulada 'dummy'.

    La pasarela dummy confirma pagos sin cobrar nada, por lo que solo es
    segura en desarrollo (DEBUG=True) o durante la suite de tests.
    """
    errors = []
    gateway = getattr(settings, 'AHHH_PAYMENT_GATEWAY', 'dummy')
    if gateway == 'dummy' and not dummy_gateway_allowed():
        errors.append(Error(
            'La pasarela de pagos "dummy" no puede usarse en produccion.',
            hint=(
                'Configura una pasarela real en AHHH_PAYMENT_GATEWAY '
                'o activa AHHH_DEBUG solo si estas en un entorno de desarrollo.'
            ),
            id='payments.E001',
        ))
    return errors
