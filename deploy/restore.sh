#!/bin/sh
# Restaura un backup de Ahhh! Ibiza: base de datos (PostgreSQL) o media.
#
# Uso (en el servidor, dentro de /opt/ahhh-ibiza):
#   sudo ./deploy/restore.sh db    backups/daily/db_ahhh_2026-08-13.sql.gz
#   sudo ./deploy/restore.sh media backups/daily/media_ahhh_2026-08-13.tar.gz
#
# La restauracion SOBREESCRIBE los datos actuales. Pide confirmacion (escribe
# RESTORE) salvo que pases --yes al final. Durante la restauracion detiene app
# y nginx (el sitio queda en mantenimiento unos segundos) y los reanuda al
# terminar. Requiere los backups generados por deploy/backup.sh (la base se
# restaura sobre la existente gracias al --clean --if-exists del dump).

set -e

# En el servidor el proyecto vive en /opt/ahhh-ibiza; en local se ejecuta
# desde el directorio actual (para pruebas).
if [ -d /opt/ahhh-ibiza ]; then
    cd /opt/ahhh-ibiza
fi

MODE="$1"
FILE="$2"
YES="$3"

if [ "$MODE" != "db" ] && [ "$MODE" != "media" ]; then
    echo "Uso: $0 {db|media} <archivo-backup> [--yes]"
    exit 1
fi

if [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
    echo "ERROR: el archivo de backup no existe: $FILE"
    exit 1
fi

if [ "$YES" != "--yes" ]; then
    echo "ATENCION: vas a SOBREESCRIBIR los datos actuales con:"
    echo "  $(basename "$FILE")"
    printf 'Escribe RESTORE para confirmar: '
    read -r CONFIRM
    if [ "$CONFIRM" != "RESTORE" ]; then
        echo "Cancelado."
        exit 0
    fi
fi

read_env() {
    grep -E "^$1=" .env 2>/dev/null | tail -n1 | cut -d= -f2- | tr -d '"' | tr -d ' \t\r'
}

DB_USER="$(read_env AHHH_POSTGRES_USER)"
DB_NAME="$(read_env AHHH_POSTGRES_DB)"
DB_USER="${DB_USER:-ahhh_user}"
DB_NAME="${DB_NAME:-ahhh_db}"

# Deja el sitio en mantenimiento (detiene app y nginx) si estan corriendo.
RESTART_APP=""
if docker compose ps -q app 2>/dev/null | grep -q .; then
    echo "Deteniendo app y nginx durante la restauracion..."
    docker compose stop app nginx >/dev/null
    RESTART_APP="1"
fi

restore_finished() {
    if [ -n "$RESTART_APP" ]; then
        echo "Reanudando app y nginx..."
        docker compose start app nginx >/dev/null
    fi
}

if [ "$MODE" = "db" ]; then
    echo "Restaurando la base de datos desde $(basename "$FILE")..."
    case "$FILE" in
        *.gz)
            if ! gunzip -c "$FILE" | docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1; then
                restore_finished
                echo "ERROR: la restauracion de la base de datos fallo."
                exit 1
            fi
            ;;
        *.sql)
            if ! docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 < "$FILE"; then
                restore_finished
                echo "ERROR: la restauracion de la base de datos fallo."
                exit 1
            fi
            ;;
        *)
            echo "ERROR: extension no soportada (usa .sql o .sql.gz)."
            restore_finished
            exit 1
            ;;
    esac
    echo "Base de datos restaurada correctamente."
    restore_finished
elif [ "$MODE" = "media" ]; then
    MEDIA_VOLUME="$(docker volume ls --format '{{.Name}}' | grep '_media_data$' | head -n1)"
    APP_IMAGE="$(docker compose images -q app 2>/dev/null | head -n1)"
    if [ -z "$MEDIA_VOLUME" ]; then
        echo "ERROR: no se encontro el volumen *_media_data."
        exit 1
    fi
    if [ -z "$APP_IMAGE" ]; then
        echo "ERROR: no se encuentra la imagen de la app (docker compose images -q app)."
        exit 1
    fi
    echo "Restaurando media desde $(basename "$FILE") al volumen $MEDIA_VOLUME..."
    BACKUP_DIR="$(cd "$(dirname "$FILE")" && pwd)"
    # --entrypoint sh: la imagen de la app tiene un entrypoint propio
    # (migrate + gunicorn) que no debe ejecutarse aqui.
    if ! docker run --rm --entrypoint sh \
        -v "$MEDIA_VOLUME:/app/media" \
        -v "$BACKUP_DIR:/backup:ro" \
        "$APP_IMAGE" \
        -c "tar xzf \"/backup/$(basename "$FILE")\" -C /app/media && chown -R appuser:appuser /app/media"; then
        restore_finished
        echo "ERROR: la restauracion de media fallo."
        exit 1
    fi
    echo "Media restaurada correctamente."
    restore_finished
fi

echo "== Restauracion completada =="
