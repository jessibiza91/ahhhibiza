from django.core.management.base import BaseCommand

from apps.ads.models import ServiceTag


DEFAULT_TAGS = [
    '24h',
    'Masajes',
    'FR natural',
    'Lesbico',
    'Sado BDSM',
    'Hoteles / domicilios',
    'Beso en la boca',
    'Griego',
    'Duplex',
    'Lluvia dorada',
    'Viajes',
    'Frances',
    'Beso negro',
    'Parejas',
    'Fiestera',
]


class Command(BaseCommand):
    help = 'Crea las categorias de servicio iniciales sin duplicar las existentes.'

    def handle(self, *args, **options):
        created_count = 0
        for tag_name in DEFAULT_TAGS:
            _tag, created = ServiceTag.objects.get_or_create(name=tag_name)
            created_count += int(created)

        self.stdout.write(self.style.SUCCESS(
            f'Categorias listas: {created_count} creadas, '
            f'{len(DEFAULT_TAGS) - created_count} ya existentes.'
        ))
