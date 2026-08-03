import os
import shutil
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
    db_path = os.path.join(root_dir, 'db.sqlite3')
    if not os.path.exists(db_path):
        print_status("[INFO] No se encontró base de datos para respaldar (es normal si es la primera vez).", YELLOW)
        return False
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = ensure_backup_dir(root_dir)
    backup_file = os.path.join(backup_dir, f"db_backup_{timestamp}.sqlite3")
    
    try:
        shutil.copy2(db_path, backup_file)
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
