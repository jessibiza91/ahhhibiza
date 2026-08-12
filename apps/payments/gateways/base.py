from abc import ABC, abstractmethod


class BaseGateway(ABC):
    """Interfaz común para las pasarelas de pago.

    Cualquier pasarela nueva debe heredar de esta clase e implementar los
    tres métodos. La pasarela activa se elige con AHHH_PAYMENT_GATEWAY
    (ver registry.py). El flujo esperado es:

      1. create_checkout(order)  -> URL donde el usuario paga.
      2. La pasarela llama al webhook al confirmar el pago.
      3. verify_webhook(request) -> autenticidad de la notificación.
      4. parse_event(request)    -> evento normalizado (exito/fallo).
    """

    name = 'base'

    @abstractmethod
    def create_checkout(self, order):
        """Crea la sesión de pago para una RechargeOrder.

        Debe devolver un dict con:
            {
                'checkout_url': str,       # URL a la que redirigir al usuario
                'gateway_order_id': str,   # referencia externa de la pasarela
            }
        """
        raise NotImplementedError

    @abstractmethod
    def verify_webhook(self, request):
        """Valida la autenticidad de un webhook recibido. Devuelve bool."""
        raise NotImplementedError

    @abstractmethod
    def parse_event(self, request):
        """Normaliza el evento del webhook en un dict:
            {
                'event_type': 'payment.succeeded' | 'payment.failed',
                'gateway_order_id': str,
                'raw': dict,
            }
        """
        raise NotImplementedError
