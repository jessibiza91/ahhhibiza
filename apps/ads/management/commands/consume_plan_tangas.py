from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from apps.ads.services import charge_daily_tangas


class Command(BaseCommand):
    help = (
        'Cobra el coste diario del plan de cada anuncio activo con plan de pago '
        '(una vez por anuncio y dia) y degrada a basico los que no pueden pagar.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo muestra lo que se haria, sin guardar cambios.',
        )
        parser.add_argument(
            '--date',
            help='Fecha a cobrar (AAAA-MM-DD). Por defecto, hoy.',
        )

    def handle(self, *args, **options):
        for_date = None
        if options.get('date'):
            try:
                for_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                raise CommandError('--date debe usar el formato AAAA-MM-DD.')

        result = charge_daily_tangas(for_date=for_date, dry_run=options['dry_run'])
        mode = 'SIMULACION (--dry-run)' if options['dry_run'] else 'COBRO DIARIO'

        self.stdout.write(self.style.MIGRATE_HEADING(f'== {mode} - {result["date"]} =='))
        for ad_id, title, action, amount in result['details']:
            if action == 'cobrar':
                self.stdout.write(
                    f'  cobrar {amount} T -> anuncio #{ad_id} "{title}"'
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'  degradar a basico (saldo insuficiente para {amount} T/dia) '
                        f'-> anuncio #{ad_id} "{title}"'
                    )
                )
        self.stdout.write(
            self.style.SUCCESS(
                f'== Total: {result["charged"]} cobrado(s), '
                f'{result["downgraded"]} degradado(s) =='
            )
        )
