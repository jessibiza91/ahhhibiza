import os
import subprocess
import sys
import time
import tempfile

# Configuration
EXTENSIONS_TO_INCLUDE = ['.py', '.html', '.css', '.js', '.bat', '.md', '.txt']
# Strict exclusions for performance and relevance
IGNORE_DIRS = ['__pycache__', 'venv', 'env', '.venv', 'node_modules', '.git', '.gemini', '.vscode', '.idea'] 
IGNORE_FILES = ['db.sqlite3', '.DS_Store', 'db_v2.sqlite3']

# Colors
GREEN = '\033[92m'
CYAN = '\033[96m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_header(msg):
    print(f"\n{BOLD}{CYAN}=== {msg} ==={RESET}")

def print_status(msg, color=RESET):
    print(f"{color}{msg}{RESET}")

def get_file_content(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return "[Error leyendo archivo]"

def format_size(size_bytes):
    return f"{size_bytes / (1024 * 1024):.2f} MB"

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print_header("AHHH IBIZA INTELLIGENT SNAPSHOT")
    
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    print_status(f"Raíz del proyecto: {root_dir}", YELLOW)
    print_status("Iniciando escaneo recursivo...\n", YELLOW)

    output_buffer = []
    tree_buffer = []
    
    file_count = 0
    total_size = 0
    scanned_dirs = set()

    start_time = time.time()

    # 1. Walk entire directory contents recursively
    for root, dirs, files in os.walk(root_dir):
        # Filtering ignored dirs
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        # Track Top-Level Dirs for Summary
        rel_path = os.path.relpath(root, root_dir)
        if rel_path != '.':
            top_level = rel_path.split(os.sep)[0]
            if top_level not in scanned_dirs and top_level not in IGNORE_DIRS:
                scanned_dirs.add(top_level)
                print(f" > Explorando: {CYAN}{top_level}/{RESET}...")

        # Build Tree
        level = 0 if rel_path == '.' else rel_path.count(os.sep) + 1
        indent = ' ' * 4 * level
        subindent = ' ' * 4 * (level + 1)
        
        folder_name = os.path.basename(root) if rel_path != '.' else 'ROOT'
        tree_buffer.append(f"{indent}[{folder_name}/]")

        for file in files:
            if file in IGNORE_FILES:
                continue
            
            # Tree Entry
            tree_buffer.append(f"{subindent}{file}")

            # Capture Content
            if any(file.endswith(ext) for ext in EXTENSIONS_TO_INCLUDE):
                full_path = os.path.join(root, file)
                rel_file_path = os.path.relpath(full_path, root_dir)
                
                try:
                    content = get_file_content(full_path)
                    size = len(content.encode('utf-8'))
                    total_size += size
                    file_count += 1
                    
                    output_buffer.append(f"\n--- FILE: {rel_file_path} ---\n")
                    output_buffer.append(content)
                except Exception as e:
                    print(f"{RED}[!] Error leyendo {file}: {e}{RESET}")

    elapsed_time = time.time() - start_time

    # Combine Output
    final_output = "=== DIRECTORY STRUCTURE ===\n" + "\n".join(tree_buffer) + "\n\n=== FILE CONTENTS ===\n" + "\n".join(output_buffer)

    # Clipboard via Temp File (PowerShell)
    clipboard_status = "NO"
    fd, temp_path = tempfile.mkstemp(suffix='.txt', text=True)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as tmp:
            tmp.write(final_output)
            
        ps_command = "Get-Content -Path '{}' -Encoding UTF8 | Set-Clipboard".format(temp_path)
        subprocess.run(["powershell", "-Command", ps_command], check=True)
        clipboard_status = "SI (PowerShell)"
        
    except Exception as e_ps:
        print(f"{YELLOW}[WARN] PowerShell copy failed: {e_ps}. Trying legacy clip...{RESET}")
        try:
            subprocess.run('clip', input=final_output, text=True, check=True, encoding='utf-16') 
            clipboard_status = "SI (Clip)"
        except Exception as e_clip:
            print(f"{RED}[!] Legacy clip also failed: {e_clip}{RESET}")
            clipboard_status = "FALLO"
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    # --- FINAL REPORT ---
    print_header("INFORME DE SNAPSHOT")
    print(f"{BOLD}Directorios Principales:{RESET} {', '.join(sorted(scanned_dirs))}")
    print(f"{BOLD}Archivos Procesados:{RESET}   {file_count}")
    print(f"{BOLD}Tamaño Total Copiado:{RESET}  {format_size(total_size)}")
    print(f"{BOLD}Tiempo de Escaneo:{RESET}     {elapsed_time:.2f}s")
    print("-" * 40)
    print(f"{BOLD}Copiado a Portapapeles:{RESET} {GREEN}{clipboard_status}{RESET}")
    print("-" * 40)
    
if __name__ == "__main__":
    main()
