import os
import subprocess
import datetime
import sys

# Setup colors
GREEN = '\033[92m'
CYAN = '\033[96m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'

def print_status(msg, color=RESET):
    print(f"{color}{msg}{RESET}")

def ensure_backup_dir(root_dir):
    backup_path = os.path.join(root_dir, 'backups', 'db')
    if not os.path.exists(backup_path):
        os.makedirs(backup_path)
    return backup_path

def create_backup(root_dir):
    backup_dir = ensure_backup_dir(root_dir)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"db_backup_{timestamp}.sql")

    try:
        with open(backup_file, 'wb') as f:
            result = subprocess.run(
                ["docker", "compose", "exec", "-T", "db", "pg_dump", "-U", "ahhh_user", "-d", "ahhh_db"],
                cwd=root_dir, stdout=f
            )
        if result.returncode != 0:
            print_status(f"[ERROR] Fallo al crear respaldo (revisa que el contenedor 'db' este arriba).", RED)
            sys.exit(1)
        print_status(f"[RESPALDO] Base de datos guardada en: {backup_file}", GREEN)
        return True
    except Exception as e:
        print_status(f"[ERROR] Fallo al crear respaldo: {e}", RED)
        sys.exit(1)

def run_migrations(root_dir):
    print_status("--- DETECTANDO CAMBIOS (MakeMigrations) ---", CYAN)
    # Using python directly to invoke manage.py
    manage_py = os.path.join(root_dir, 'manage.py')
    
    # 1. Makemigrations
    result_make = subprocess.run([sys.executable, manage_py, 'makemigrations'], cwd=root_dir)
    if result_make.returncode != 0:
        print_status("[ERROR] Fallo en makemigrations.", RED)
        return

    print_status("--- APLICANDO CAMBIOS (Migrate) ---", CYAN)
    # 2. Migrate
    result_migrate = subprocess.run([sys.executable, manage_py, 'migrate'], cwd=root_dir)
    if result_migrate.returncode != 0:
        print_status("[ERROR] Fallo en migrate.", RED)
    else:
        print_status("[EXITO] Sistema actualizado correctamente.", GREEN)

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print_status("=== SMART MIGRATION SYSTEM ===", CYAN)
    
    # Determine Root Dir (maintenance/migrations/ -> ../../)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(current_dir))
    
    # 1. Backup
    create_backup(root_dir)
    
    # 2. Migrate
    run_migrations(root_dir)

if __name__ == "__main__":
    os.system('color')
    main()
