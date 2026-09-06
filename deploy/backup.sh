#!/bin/sh
# Backup diario de Ahhh! Ibiza: base de datos (PostgreSQL) + media de usuarios.
#
# Uso (en el servidor, dentro de /opt/ahhh-ibiza):
#   sudo ./deploy/backup.sh
#
# Genera en backups/:
#   daily/db_ahhh_YYYY-MM-DD.sql.gz      dump completo de la base (incluye
#                                        transacciones, ordenes de recarga,
#                                        saldos de Tangas y logs de webhook)
#   daily/media_ahhh_YYYY-MM-DD.tar.gz   archivos subidos por los usuarios
#   monthly/                              copia del 1er dia de cada mes (no se
#                                        rota; historico contable a largo plazo)
#
# La rotacion se hace por la fecha del NOMBRE del archivo (no por mtime), de
# forma que si el cron no corre un dia no se borran copias por error.
# Cuantas copias diarias se conservan se controla con AHHH_BACKUP_RETENTION_DAYS
# del .env (por defecto 14).

set -e

# En el servidor el proyecto vive en /opt/ahhh-ibiza; en local se ejecuta
# desde el directorio actual (para pruebas).
if [ -d /opt/ahhh-ibiza ]; then
    cd /opt/ahhh-ibiza
fi

BACKUP_DIR="$PWD/backups"
TODAY="$(date +%F)"

read_env() {
    grep -E "^$1=" .env 2>/dev/null | tail -n1 | cut -d= -f2- | tr -d '"' | tr -d ' \t\r'
}

DB_USER="$(read_env AHHH_POSTGRES_USER)"
DB_NAME="$(read_env AHHH_POSTGRES_DB)"
RETENTION="$(read_env AHHH_BACKUP_RETENTION_DAYS)"

DB_USER="${DB_USER:-ahhh_user}"
DB_NAME="${DB_NAME:-ahhh_db}"
RETENTION="${RETENTION:-14}"

mkdir -p "$BACKUP_DIR/daily" "$BACKUP_DIR/monthly"
echo "== Backup de Ahhh! Ibiza ($TODAY) =="

# 1. Base de datos: pg_dump consistente, comprimido y verificado.
# --clean --if-exists: el dump incluye DROP TABLE, lo que permite restaurarlo
# sobre una base existente sin errores (ver deploy/restore.sh).
TMP_DB="$BACKUP_DIR/daily/.tmp_db_$TODAY.sql"
FINAL_DB="$BACKUP_DIR/daily/db_ahhh_$TODAY.sql.gz"
if docker compose exec -T db pg_dump --clean --if-exists -U "$DB_USER" "$DB_NAME" > "$TMP_DB"; then
    gzip -f "$TMP_DB"
    mv "$TMP_DB.gz" "$FINAL_DB"
    if gzip -t "$FINAL_DB"; then
        echo "DB ok:        $(basename "$FINAL_DB")"
    else
        echo "ERROR: el dump de DB esta corrupto."
        exit 1
    fi
else
    rm -f "$TMP_DB"
    echo "ERROR: no se pudo hacer pg_dump. ?Esta levantado el contenedor db?"
    exit 1
fi

# 2. Media de usuarios: tar comprimido del volumen.
TMP_MEDIA="$BACKUP_DIR/daily/.tmp_media_$TODAY.tar"
FINAL_MEDIA="$BACKUP_DIR/daily/media_ahhh_$TODAY.tar.gz"
MEDIA_VOLUME="$(docker volume ls --format '{{.Name}}' | grep '_media_data$' | head -n1)"
if [ -n "$MEDIA_VOLUME" ]; then
    if docker run --rm -v "$MEDIA_VOLUME:/data:ro" -v "$BACKUP_DIR/daily:/backup" \
        alpine tar czf "/backup/$(basename "$TMP_MEDIA").gz" -C /data .; then
        mv "$TMP_MEDIA.gz" "$FINAL_MEDIA"
        if gzip -t "$FINAL_MEDIA"; then
            echo "Media ok:     $(basename "$FINAL_MEDIA")"
        else
            echo "ERROR: el tar de media esta corrupto."
            exit 1
        fi
    else
        rm -f "$TMP_MEDIA.gz"
        echo "ERROR: no se pudo comprimir la media."
        exit 1
    fi
else
    echo "AVISO: no se encontro el volumen *_media_data; no se respalda la media."
fi

# 3. Archivo mensual (1er dia del mes): se conserva, no se rota.
if [ "$(date +%d)" = "01" ]; then
    if [ -f "$FINAL_DB" ]; then
        cp -n "$FINAL_DB" "$BACKUP_DIR/monthly/" && echo "Mensual:       $(basename "$FINAL_DB")"
    fi
fi

# 4. Rotacion de las copias diarias (por la fecha del nombre).
rotated=0
for f in "$BACKUP_DIR"/daily/db_ahhh_*.sql.gz "$BACKUP_DIR"/daily/media_ahhh_*.tar.gz; do
    [ -f "$f" ] || continue
    filedate="$(basename "$f" | sed -E 's/.*_([0-9]{4}-[0-9]{2}-[0-9]{2}).*/\1/')"
    case "$filedate" in
        [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) ;;
        *) continue ;;
    esac
    age=$(( ( $(date -d "$TODAY" +%s) - $(date -d "$filedate" +%s) ) / 86400 ))
    if [ "$age" -gt "$RETENTION" ]; then
        echo "Rotando:      $(basename "$f")"
        rm -f "$f"
        rotated=$((rotated + 1))
    fi
done
echo "Rotacion:      $rotated copia(s) retirada(s) (retencion $RETENTION dias)."

echo "== Backup completado =="
