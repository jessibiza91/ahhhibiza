from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings

class Command(BaseCommand):
    help = 'Crea el superusuario Patricia si no existe'

    def handle(self, *args, **options):
        User = get_user_model()
        username = 'Patricia'
        password = 'Aa@123456'
        
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
