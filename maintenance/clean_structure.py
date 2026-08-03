import os
import shutil
from pathlib import Path

SKIP_DIRS = {
    '.git',
    '.venv',
    'venv',
    'media',
    'backups',
    'node_modules',
}

def should_skip(path):
    return any(part in SKIP_DIRS for part in path.parts)

def clean_structure():
    root_dir = Path(__file__).resolve().parent.parent

    # Safeguard active DB and migrations. This cleaner only removes generated
    # Python cache artifacts; schema files and databases are never touched here.
    for cache_dir in root_dir.rglob('__pycache__'):
        if should_skip(cache_dir.relative_to(root_dir)):
            continue
        if cache_dir.is_dir():
            try:
                shutil.rmtree(cache_dir)
                print(f"[-] Deleted pycache: {cache_dir}")
            except Exception as e:
                print(f"[!] Error deleting {cache_dir}: {e}")

    for pyc_file in root_dir.rglob('*.pyc'):
        if should_skip(pyc_file.relative_to(root_dir)):
            continue
        try:
            os.remove(pyc_file)
            print(f"[-] Deleted pyc: {pyc_file}")
        except Exception as e:
            print(f"[!] Error deleting {pyc_file}: {e}")

if __name__ == "__main__":
    print("--- STARTING CLEANUP ---")
    clean_structure()
    print("--- CLEANUP COMPLETE ---")
