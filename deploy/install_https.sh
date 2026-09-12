#!/bin/sh
# Instala/renueva el certificado SSL de Ahhh! Ibiza (Let's Encrypt).
#
# Uso (en el servidor, dentro de /opt/ahhh-ibiza):
#   sudo ./deploy/install_https.sh              # usa AHHH_DOMAIN del .env
#   sudo ./deploy/install_https.sh midominio.com # o pasa el dominio como argumento
#
# Se puede ejecutar las veces que quieras:
#   1. Crea un certificado autofirmado temporal para que nginx pueda arrancar
#      aunque el dominio todavia no apunte al servidor.
#   2. Si el dominio ya apunta al servidor, emite el certificado real. Solo
#      incluye www si www.DOMINIO resuelve en DNS; si no, emite solo el dominio.
#   3. Activa la renovacion automatica (timer ahhh-certbot-renew).
#
# Nota: el certificado autofirmado se aparta a una carpeta propia mientras
# certbot emite el real, para que "live/$DOMAIN" quede libre (certbot se niega
# a escribir sobre una carpeta live ya existente). Si la emision falla, el
# temporal se restaura y el sitio sigue funcionando.

set -e

cd /opt/ahhh-ibiza

DOMAIN="${1:-$(grep -E '^AHHH_DOMAIN=' .env 2>/dev/null | tail -n1 | cut -d= -f2- | tr -d '"' | tr -d ' \t\r' )}"
DOMAIN="${DOMAIN:-ahhh-ibiza.com}"

WEBROOT=/opt/ahhh-ibiza/deploy/certbot/www
LIVE_DIR=/etc/letsencrypt/live/$DOMAIN
BOOTSTRAP_DIR=/etc/letsencrypt/ahhh-bootstrap/$DOMAIN

if ! command -v openssl >/dev/null 2>&1; then
    echo "ERROR: falta openssl. Instalo:  sudo apt install -y openssl"
    exit 1
fi

mkdir -p "$WEBROOT" "$BOOTSTRAP_DIR"

# Certificado temporal autofirmado: permite que nginx arranque con el bloque
# 443 del conf incluso antes de tener el certificado real.
if [ ! -f "$LIVE_DIR/fullchain.pem" ]; then
    echo "Creando certificado temporal autofirmado para $DOMAIN..."
    mkdir -p "$LIVE_DIR"
    openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
        -keyout "$LIVE_DIR/privkey.pem" \
        -out "$LIVE_DIR/fullchain.pem" \
        -subj "/CN=$DOMAIN"
fi

# Asegura que nginx este levantado (sirve el reto webroot en /.well-known/acme-challenge/).
docker compose up -d nginx

# Certificado real de Let's Encrypt (solo si el dominio ya resuelve al servidor).
if command -v certbot >/dev/null 2>&1; then
    if ! certbot certificates 2>/dev/null | grep -qF "$DOMAIN"; then
        # Aparta el temporal: certbot no emite sobre una carpeta live existente.
        if [ -f "$LIVE_DIR/fullchain.pem" ] && [ ! -f "$BOOTSTRAP_DIR/fullchain.pem" ]; then
            cp "$LIVE_DIR/fullchain.pem" "$BOOTSTRAP_DIR/fullchain.pem"
            cp "$LIVE_DIR/privkey.pem" "$BOOTSTRAP_DIR/privkey.pem"
            echo "Apartando el certificado temporal para dejar libre el directorio live..."
        fi
        rm -rf "$LIVE_DIR"

        # www solo se incluye si resuelve en DNS (el dominio debe apuntar aqui).
        EXTRA_DOMAINS=""
        if getent hosts "www.$DOMAIN" >/dev/null 2>&1; then
            EXTRA_DOMAINS="-d www.$DOMAIN"
            echo "www.$DOMAIN resuelve: el certificado cubre $DOMAIN y www.$DOMAIN."
        else
            echo "AVISO: www.$DOMAIN no resuelve en DNS; el certificado cubrira solo $DOMAIN."
        fi

        echo "Solicitando certificado real de Let's Encrypt para $DOMAIN..."
        if certbot certonly --webroot -w "$WEBROOT" \
            --non-interactive --agree-tos --register-unsafely-without-email \
            -d "$DOMAIN" $EXTRA_DOMAINS; then
            echo "Certificado real emitido para $DOMAIN."
            rm -rf "$BOOTSTRAP_DIR"
        else
            echo "No se pudo emitir el certificado real (el dominio debe apuntar a este"
            echo "servidor y permitir el puerto 80)."
            echo "Restaurando el certificado temporal; el sitio sigue funcionando."
            rm -rf "$LIVE_DIR"
            mkdir -p "$LIVE_DIR"
            [ -f "$BOOTSTRAP_DIR/fullchain.pem" ] && cp "$BOOTSTRAP_DIR/fullchain.pem" "$LIVE_DIR/fullchain.pem"
            [ -f "$BOOTSTRAP_DIR/privkey.pem" ] && cp "$BOOTSTRAP_DIR/privkey.pem" "$LIVE_DIR/privkey.pem"
        fi
    else
        echo "Ya existe un certificado para $DOMAIN. No se vuelve a emitir."
    fi
else
    echo "AVISO: certbot no esta instalado, no se solicita el certificado real."
    echo "Cuando lo instales (sudo apt install -y certbot), ejecuta de nuevo este script."
fi

# Recarga nginx para que use el certificado actual.
docker compose exec -T nginx nginx -s reload

# Renovacion automatica: timer de systemd que ejecuta deploy/ssl_renew.sh.
cp deploy/systemd/ahhh-certbot-renew.service /etc/systemd/system/
cp deploy/systemd/ahhh-certbot-renew.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now ahhh-certbot-renew.timer

echo "Listo. La renovacion automatica esta activa:"
echo "  systemctl status ahhh-certbot-renew.timer"