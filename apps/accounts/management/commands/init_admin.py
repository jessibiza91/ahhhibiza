import os

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Crea el superusuario Patricia si no existe'

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.getenv('AHHH_ADMIN_USERNAME', 'Patricia')
        password = os.getenv('AHHH_ADMIN_PASSWORD')

        if not password:
            raise CommandError(
                'AHHH_ADMIN_PASSWORD no esta definido. Configuralo en el archivo .env antes de ejecutar este comando.'
            )

        # Colors (ANSI)
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RESET = '\033[0m'
        
        self.stdout.write(f"[INFO] Buscando a {username}...")

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email='', password=password)
            self.stdout.write(f"{GREEN}[OK] {username} creada correctamente.{RESET}")
        else:
            self.stdout.write(f"{YELLOW}[WARN] Patricia ya existe{RESET}")
