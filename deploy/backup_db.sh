#!/bin/sh
#
# backup_db.sh - Copia de seguridad automatica de la base de datos PostgreSQL.
#
# Genera un pg_dump comprimido (gzip) de la base que gestiona docker-compose,
# lo guarda en el directorio de backups del servidor y rota los dumps antiguos.
#
# Ademas, si configuras un remote de rclone hacia Backblaze B2 (o cualquier
# otro destino compatible), sube cada dump a ese destino off-site para
# protegerte de fallos del propio servidor.
#
# Disenado para ejecutarse desde cron. Requiere estar en el directorio del
# proyecto (/opt/ahhh-ibiza) para leer el .env con las credenciales.
#
# Pre-requisitos en el servidor:
#   - docker ejecutable en el PATH (el contenedor ahhh_postgres debe correr).
#   - rclone instalado y configurado (opcional, solo si quieres copia off-site):
#       sudo apt install -y rclone
#       rclone config          # crea un remote, p.ej. "ahhh-b2" de tipo b2
#     Despues define AHHH_B2_REMOTE en el .env (ver abajo).
#
set -e

# --- Configuracion -----------------------------------------------------------

# Directorio raiz del proyecto (por defecto /opt/ahhh-ibiza, sobreescribible).
PROJECT_DIR="${AHHH_BACKUP_DIR:-/opt/ahhh-ibiza}"

# Directorio donde se guardan los dumps.
BACKUP_DIR="$PROJECT_DIR/backups"

# Numero de dumps locales que se conservan (los mas recientes).
KEEP="${AHHH_BACKUP_KEEP:-14}"

# Nombre del contenedor de PostgreSQL definido en docker-compose.yml.
DB_CONTAINER="ahhh_postgres"

LOG_FILE="$BACKUP_DIR/backup.log"

# Remote de rclone hacia Backblaze B2 y carpeta de destino, vacios por defecto.
# Ejemplos:
#   AHHH_B2_REMOTE=ahhh-b2:ahhh-ibiza-backups
# Ponerlos en el .env hace que cada dump se suba a B2 (off-site).
B2_REMOTE="${AHHH_B2_REMOTE:-}"

# --- Cargar credenciales desde el .env --------------------------------------

ENV_FILE="$PROJECT_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
  echo "[$(date '+%F %T')] ERROR: no existe $ENV_FILE" >> "$LOG_FILE"
  exit 1
fi

DB_NAME="${AHHH_POSTGRES_DB:-}"
DB_USER="${AHHH_POSTGRES_USER:-}"
DB_PASS="${AHHH_POSTGRES_PASSWORD:-}"

# El .env usa claves AHHH_POSTGRES_*; si no estan exportadas en el entorno,
# se leen del propio archivo.
_cred() {
  grep -E "^$1=" "$ENV_FILE" | head -n1 | cut -d= -f2-
}

[ -z "$DB_NAME" ] && DB_NAME="$(_cred AHHH_POSTGRES_DB)"
[ -z "$DB_USER" ] && DB_USER="$(_cred AHHH_POSTGRES_USER)"
[ -z "$DB_PASS" ] && DB_PASS="$(_cred AHHH_POSTGRES_PASSWORD)"
[ -z "$B2_REMOTE" ] && B2_REMOTE="$(_cred AHHH_B2_REMOTE)"

if [ -z "$DB_NAME" ] || [ -z "$DB_USER" ] || [ -z "$DB_PASS" ]; then
  echo "[$(date '+%F %T')] ERROR: AHHH_POSTGRES_* no definidas en el entorno" >> "$LOG_FILE"
  exit 1
fi

# Para que el backup no dependa de que `docker compose` pueda releer el .env
# (p.ej. una linea invalida rompe su parser), hablamos directamente al
# contenedor con `docker exec` y le pasamos el password via PGPASSWORD.
# PGPASSWORD solo existe dentro del proceso, no aparece en la lista de
# procesos del sistema, y desaparece al terminar el script.

# --- Crear directorio --------------------------------------------------------

mkdir -p "$BACKUP_DIR"

# --- Generar el dump comprimido ----------------------------------------------

TS="$(date '+%Y-%m-%d_%H-%M-%S')"
DUMP_FILE="$BACKUP_DIR/ahhh_db_${TS}.sql.gz"

# Nota: /bin/sh (dash) no soporta pipefail ni PIPESTATUS. Hacemos el dump a un
# archivo temporal primero (para capturar el exit code de docker) y luego lo
# comprimimos, que es 100% portable.
RAW_FILE="$BACKUP_DIR/.tmp_$$.sql"

if ! PGPASSWORD="$DB_PASS" docker exec \
    "$DB_CONTAINER" \
    pg_dump -U "$DB_USER" "$DB_NAME" > "$RAW_FILE"; then
  rm -f "$RAW_FILE"
  echo "[$(date '+%F %T')] ERROR: fallo pg_dump de $DB_NAME" >> "$LOG_FILE"
  exit 1
fi

gzip -c "$RAW_FILE" > "$DUMP_FILE"
rm -f "$RAW_FILE"
echo "[$(date '+%F %T')] OK $DUMP_FILE" >> "$LOG_FILE"

# --- Subida off-site a Backblaze B2 (via rclone) -----------------------------

# Si AHHH_B2_REMOTE esta definido, copia el dump al destino remoto. Se intenta
# 3 veces con respiro por si hay un error de red transitorio. Si falla por fin,
# se aborta con error para que quede constancia en el log y en cron, pero nunca
# se borra el dump local por un fallo de subida.
if [ -n "$B2_REMOTE" ]; then
  if ! command -v rclone >/dev/null 2>&1; then
    echo "[$(date '+%F %T')] ERROR: AHHH_B2_REMOTE definido pero rclone no esta instalado" >> "$LOG_FILE"
    exit 1
  fi

  ATTEMPT=1
  UPLOAD_OK=0
  while [ "$ATTEMPT" -le 3 ]; do
    if rclone copy "$DUMP_FILE" "$B2_REMOTE" >> "$LOG_FILE" 2>&1; then
      UPLOAD_OK=1
      break
    else
      echo "[$(date '+%F %T')] AVISO: subida a B2 fallida (intento $ATTEMPT/3)" >> "$LOG_FILE"
      ATTEMPT=$((ATTEMPT + 1))
      [ "$ATTEMPT" -le 3 ] && sleep 5
    fi
  done

  if [ "$UPLOAD_OK" -eq 1 ]; then
    echo "[$(date '+%F %T')] OK subida a B2: $B2_REMOTE" >> "$LOG_FILE"
  else
    echo "[$(date '+%F %T')] ERROR: no se pudo subir el dump a B2" >> "$LOG_FILE"
    exit 1
  fi
fi

# --- Rotar dumps antiguos ----------------------------------------------------

# Borrar los dumps locales que superen KEEP, conservando la ultima copia.
ls -1t "$BACKUP_DIR"/ahhh_db_*.sql.gz 2>/dev/null \
  | tail -n +"$((KEEP + 1))" \
  | while read -r old; do rm -f "$old"; done

# Limpiar tambien el log si crece demasiado (se queda con las ultimas 200 lineas).
tail -n 200 "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"

exit 0
