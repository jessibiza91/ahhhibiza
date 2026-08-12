from django.urls import reverse

from .base import BaseGateway


class DummyGateway(BaseGateway):
    """Pasarela simulada para desarrollo.

    Permite probar todo el ciclo de recarga sin salir del sitio ni tener
    credenciales reales: el "checkout" es una URL local de confirmación.
    Solo se permite con AHHH_DEBUG=True; en produccion el system check
    (payments.E001) y el registry bloquean su uso.
    Sustituir por una subclase real de BaseGateway cuando se elija pasarela.
    """

    name = 'dummy'

    def create_checkout(self, order):
        return {
            'checkout_url': reverse(
                'payments:recharge_success',
                kwargs={'order_id': order.id},
            ),
            'gateway_order_id': f'dummy-{order.id}',
        }

    def verify_webhook(self, request):
        # Solo desarrollo: no hay firma que validar. Las pasarelas reales
        # deberán verificar la firma del payload.
        return True

    def parse_event(self, request):
        return {
            'event_type': 'payment.succeeded',
            'gateway_order_id': request.POST.get('gateway_order_id', ''),
            'raw': dict(request.POST),
        }
