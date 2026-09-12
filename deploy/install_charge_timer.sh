#!/bin/sh
# Instala el cobro diario de Tangas de Ahhh! Ibiza (timer systemd).
#
# Uso (en el servidor, dentro de /opt/ahhh-ibiza):
#   sudo ./deploy/install_charge_timer.sh
#
# Genera /etc/systemd/system/ahhh-tangas-charge.timer a partir de la variable
# AHHH_TANGAS_CHARGE_HOUR del .env (formato HH:MM, por defecto 02:45) porque
# systemd no puede leer variables de entorno en OnCalendar, copia la unidad de
# servicio y activa el timer. Se puede ejecutar las veces que quieras.

set -e

cd /opt/ahhh-ibiza

HOUR="$(grep -E '^AHHH_TANGAS_CHARGE_HOUR=' .env 2>/dev/null | tail -n1 | cut -d= -f2- | tr -d '"' | tr -d ' \t\r')"
HOUR="${HOUR:-02:45}"

case "$HOUR" in
    [0-2][0-9]:[0-5][0-9]) ;;
    *)
        echo "ERROR: AHHH_TANGAS_CHARGE_HOUR invalido ($HOUR). Usa formato HH:MM."
        exit 1
        ;;
esac
HH="${HOUR%%:*}"
if [ "$HH" -gt 23 ]; then
    echo "ERROR: AHHH_TANGAS_CHARGE_HOUR invalido ($HOUR). Las horas van de 00 a 23."
    exit 1
fi

cp deploy/systemd/ahhh-tangas-charge.service /etc/systemd/system/

# systemd OnCalendar no admite variables: generamos el timer con la hora del .env.
sed "s/^OnCalendar=.*/OnCalendar=*-*-* $HOUR:00/" \
    deploy/systemd/ahhh-tangas-charge.timer \
    > /etc/systemd/system/ahhh-tangas-charge.timer

systemctl daemon-reload
systemctl enable --now ahhh-tangas-charge.timer

echo "Cobro diario de Tangas activo a las $HOUR (con retardo aleatorio de 30 min):"
echo "  systemctl status ahhh-tangas-charge.timer"
