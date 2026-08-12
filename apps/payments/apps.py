from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    name = 'apps.payments'

    def ready(self):
        from . import checks  # noqa: F401
