#!/bin/sh
# Renovacion automatica del certificado SSL (la ejecuta el timer systemd
# ahhh-certbot-renew). Renueva solo cuando falta menos de un mes y recarga
# nginx para que sirva el certificado nuevo sin cortar el servicio.
#
# No requiere cortar nginx: usa el reto webroot de Let's Encrypt (nginx sirve
# /.well-known/acme-challenge/ desde el webroot montado en docker-compose.yml).

set -e

cd /opt/ahhh-ibiza

certbot renew --quiet

docker compose exec -T nginx nginx -s reload
