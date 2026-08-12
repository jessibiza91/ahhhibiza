from django.core.management.base import BaseCommand

from apps.payments.models import TangasPackage


DEFAULT_PACKAGES = [
    {
        'name': 'Pack Inicio',
        'tangas_amount': 50,
        'price_eur': '15.00',
        'sort_order': 1,
    },
    {
        'name': 'Pack Pro',
        'tangas_amount': 150,
        'price_eur': '40.00',
        'sort_order': 2,
    },
    {
        'name': 'Pack VIP',
        'tangas_amount': 300,
        'price_eur': '75.00',
        'sort_order': 3,
    },
]


class Command(BaseCommand):
    help = 'Crea los paquetes de Tangas iniciales sin duplicar ni pisar los existentes.'

    def handle(self, *args, **options):
        created_count = 0
        for package_data in DEFAULT_PACKAGES:
            _package, created = TangasPackage.objects.get_or_create(
                name=package_data['name'],
                defaults={
                    'tangas_amount': package_data['tangas_amount'],
                    'price_eur': package_data['price_eur'],
                    'sort_order': package_data['sort_order'],
                },
            )
            created_count += int(created)

        self.stdout.write(self.style.SUCCESS(
            f'Paquetes listos: {created_count} creados, '
            f'{len(DEFAULT_PACKAGES) - created_count} ya existentes.'
        ))
