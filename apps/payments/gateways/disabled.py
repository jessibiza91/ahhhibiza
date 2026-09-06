from .base import BaseGateway


class DisabledGateway(BaseGateway):
    """Pasarela deshabilitada.

    Se usa en produccion cuando aun no se ha integrado una pasarela real.
    La recarga de Tangas queda bloqueada: el usuario ve un mensaje
    indicando que la funcion no esta disponible.
    """

    name = 'disabled'

    def create_checkout(self, order):
        raise ValueError(
            'La recarga de Tangas no esta disponible temporalmente. '
            'Contacta con soporte si necesitas saldo.'
        )

    def verify_webhook(self, request):
        return False

    def parse_event(self, request):
        return {}
