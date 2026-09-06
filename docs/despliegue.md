# Despliegue - Ahhh! Ibiza (Docker)

Guía paso a paso para subir el proyecto a un servidor (VPS) con Docker.
Está pensada para que la siga una persona sin experiencia previa en despliegues.

## 1. Que se instala

El proyecto se ejecuta como 4 contenedores orquestados por Docker Compose:

| Servicio | Imagen             | Para que sirve                                   |
| -------- | ------------------ | ------------------------------------------------ |
| `db`     | postgres:16        | Base de datos PostgreSQL                         |
| `redis`  | redis:7-alpine     | Cache compartida del rate limiting               |
| `app`    | (construida)       | Django con gunicorn (Django 6 + Python 3.13)     |
| `nginx`  | nginx:1.27-alpine  | Proxy inverso, sirve /static/ y /media/          |

Además, `deploy/systemd/ahhh.service` permite gestionar todo con `systemctl`.

## 2. Requisitos del servidor

- Ubuntu 22.04/24.04 (u otra distro con `systemd`)
- Docker y el plugin Docker Compose v2:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
```

- `certbot` y `openssl` (para el certificado SSL de Let's Encrypt):

```bash
sudo apt install -y certbot openssl
```

- (Obligatorio) un dominio apuntando al IP del servidor (registro A de
  `tu-dominio.com` y `www.tu-dominio.com`) y los puertos 80/443 abiertos.

## 3. Archivos de despliegue (ya en el repo)

```
Dockerfile                 Imagen de la app (dependencias prod + entrypoint)
.dockerignore              Excluye venv, media, .env, .git del build
deploy/entrypoint.sh       migrate + init_admin + collectstatic + gunicorn
deploy/install_https.sh    Certificado SSL: temporal + Let's Encrypt + renovacion
deploy/ssl_renew.sh        Renovacion del certificado (lo ejecuta el timer)
deploy/certbot/www/        Webroot para el reto ACME de Let's Encrypt
deploy/nginx/ahhh.conf     Configuracion de nginx (HTTPS, static, media, reto ACME)
deploy/backup.sh           Copia de seguridad diaria (DB + media) + rotacion
deploy/restore.sh          Restauracion de una copia (DB o media)
deploy/install_charge_timer.sh  Instala el timer del cobro diario de Tangas
deploy/systemd/ahhh.service  Unidad systemd que arranca/para el stack
deploy/systemd/ahhh-backup.service/.timer         Copias de seguridad diarias (03:15)
deploy/systemd/ahhh-certbot-renew.service/.timer  Renovacion automatica del SSL
deploy/systemd/ahhh-tangas-charge.service/.timer  Cobro diario de Tangas de los planes
deploy/backup_db.sh        Backup automatico de PostgreSQL (+ opcion B2/rclone)
deploy/cron/ahhh_backup    Cron diario (03:00) que ejecuta backup_db.sh
docker-compose.yml         Orquesta db, redis, app y nginx
requirements/prod.txt      Dependencias de produccion (gunicorn, redis)
```

## 4. Primer despliegue (paso a paso)

### 4.1 Clonar el repositorio

```bash
sudo mkdir -p /opt
sudo git clone <url-del-repositorio> /opt/ahhh-ibiza
cd /opt/ahhh-ibiza
```

### 4.2 Crear el `.env`

```bash
sudo cp .env.example .env
sudo nano .env
```

Configura al menos estos valores:

```ini
AHHH_DEBUG=false
AHHH_SECRET_KEY=<genera una clave larga y aleatoria>
AHHH_ALLOWED_HOSTS=tu-dominio.com,www.tu-dominio.com
AHHH_CSRF_TRUSTED_ORIGINS=https://tu-dominio.com,https://www.tu-dominio.com
AHHH_DOMAIN=tu-dominio.com
AHHH_PUBLIC_BASE_URL=https://www.tu-dominio.com
AHHH_POSTGRES_DB=ahhh_db
AHHH_POSTGRES_USER=ahhh_user
AHHH_POSTGRES_PASSWORD=<contraseña segura de la base de datos>
AHHH_ADMIN_USERNAME=Patricia
AHHH_ADMIN_PASSWORD=<contraseña del superadmin>
AHHH_ADMIN_EMAIL=patricia@tu-dominio.com
AHHH_AUTH_RATE=5/h
AHHH_EMAIL_HOST=<servidor SMTP del proveedor>
AHHH_EMAIL_HOST_USER=<usuario del SMTP>
AHHH_EMAIL_HOST_PASSWORD=<contraseña del SMTP>
AHHH_DEFAULT_FROM_EMAIL=Ahhh! Ibiza <noreply@tu-dominio.com>
```

Para generar una clave segura:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

Notas:

- `AHHH_DB_HOST` y `AHHH_DB_PORT` NO se tocan: dentro de la red Docker la
  app conecta a la base por el nombre de servicio `db`.
- `AHHH_REDIS_URL` tampoco: el contenedor `app` ya la inyecta
  (`redis://redis:6379/1`).
- `AHHH_DOMAIN` se usa para emitir y renovar el certificado SSL; debe ser el
  dominio sin `www` ni `https://` y coincidir con el de `deploy/nginx/ahhh.conf`.
- **Correo (SMTP)**: el flujo "¿Olvidaste tu contraseña?" necesita un SMTP real
  (`AHHH_EMAIL_HOST` y credenciales). Sin ellas, el proyecto usa el backend de
  consola: los correos se imprimen en el log del contenedor `app` y no se
  envían. Si aún no tienes SMTP configurado, el resto del sitio funciona igual.
- **Superadmin**: `init_admin` crea el superusuario con `AHHH_ADMIN_USERNAME` /
  `AHHH_ADMIN_PASSWORD` del `.env`. Con `AHHH_ADMIN_EMAIL` definido, además le
  asigna ese correo (idempotente, sin tocar la contraseña) para que la
  recuperación por email le funcione. Sin correo, la contraseña se recupera por
  el servidor: `sudo docker compose exec app python manage.py changepassword Patricia`.
- El `.env` no debe versionarse ni compartirse.

### 4.3 Preparar el certificado (obligatorio antes del primer arranque)

nginx ya escucha en el puerto 443 (ver `deploy/nginx/ahhh.conf`), así que
necesita un certificado para arrancar. El script `install_https.sh` crea uno
autofirmado temporal (el sitio funciona aunque el dominio todavía no apunte) y,
si el dominio ya resuelve al servidor, emite directamente el real de Let's
Encrypt. Además activa la renovación automática.

```bash
cd /opt/ahhh-ibiza
sudo ./deploy/install_https.sh
```

> Requiere `openssl` (obligatorio) y `certbot` (recomendado para el
> certificado real) instalados en el host (sección 2). Si `certbot` no está,
> el script solo crea el temporal y te avisa para que lo instales y repitas.

El script es idempotente: repítelo más adelante (cuando el dominio apunte al
servidor) para pasar del certificado temporal al real.

### 4.4 Arrancar el stack

```bash
sudo docker compose up -d --build
```

En el primer arranque el contenedor `app` ejecuta automáticamente:

1. `migrate` (crea el esquema en PostgreSQL)
2. `init_admin` (crea el superadmin, idempotente)
3. `collectstatic` (recoge CSS/JS en `staticfiles/`)

Espera a que nginx esté sano:

```bash
sudo docker compose ps
```

Debes ver los 4 contenedores `Up` y con estado `(healthy)`.

### 4.5 Verificar

```bash
curl https://localhost/health/ -k
# -> {"status": "ok"}
```

- `-k` ignora el certificado autofirmado temporal. Cuando el certificado real
  esté activo, `curl https://tu-dominio.com/health/` funciona sin `-k`.
- Abre `https://tu-dominio.com` en el navegador. Con el certificado temporal el
  navegador mostrará una advertencia de seguridad: es esperable hasta que el
  dominio apunte al servidor y se ejecute de nuevo `install_https.sh`.

Abre `https://tu-dominio.com/admin/` en el navegador y entra con el
superadmin para comprobar el panel.

## 5. Gestionar el stack con systemd

Instala la unidad (una vez):

```bash
sudo cp deploy/systemd/ahhh.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ahhh
sudo systemctl start ahhh
```

Comandos útiles:

```bash
sudo systemctl status ahhh   # estado
sudo systemctl restart ahhh  # reinicia los contenedores
sudo systemctl stop ahhh     # para todo el stack
```

La unidad ejecuta `docker compose up -d` desde `/opt/ahhh-ibiza`. Los
contenedores arrancan solos al encender el servidor (`restart: unless-stopped`
+ `enable`).

## 6. Actualizar el proyecto

```bash
cd /opt/ahhh-ibiza
sudo git pull
sudo docker compose build app     # reconstruye la imagen con el nuevo codigo
sudo docker compose up -d         # recrea solo lo que cambio
```

O con systemd:

```bash
sudo systemctl restart ahhh
```

Los datos de la base, media y redis viven en volúmenes Docker
(`pg_data`, `media_data`, `static_data`, `redis_data`): sobreviven a los
`up`/`down` y a los reinicios.

## 7. HTTPS: certificado real de Let's Encrypt

El stack ya sirve por HTTPS desde el primer arranque, pero con un certificado
autofirmado temporal (el navegador muestra advertencia). Para obtener el
certificado real:

1. Apunta tu dominio al IP del servidor (registro A para `tu-dominio.com` y
   `www.tu-dominio.com`) y abre los puertos 80 y 443 en el firewall. Let's
   Encrypt valida el reto a través del puerto 80.

2. Instala `certbot` en el host (si no está):

   ```bash
   sudo apt install -y certbot openssl
   ```

3. Ejecuta de nuevo el mismo script del paso 4.3 (esta vez emitirá el
   certificado real, sin cortar el servicio):

   ```bash
   cd /opt/ahhh-ibiza
   sudo ./deploy/install_https.sh
   ```

4. Verifica:

   ```bash
   curl https://tu-dominio.com/health/
   # -> {"status": "ok"}   (sin -k: certificado real válido)
   ```

Cómo funciona:

- `install_https.sh` usa el reto **webroot** (nginx sirve
  `/.well-known/acme-challenge/` desde el webroot montado), así que no hay que
  parar nginx para emitir ni renovar.
- El mismo script ya activó la **renovación automática** en el paso 4.3: el
  timer `ahhh-certbot-renew` ejecuta `deploy/ssl_renew.sh` a diario y solo
  renueva cuando faltan menos de 30 días, recargando nginx sin cortar el
  servicio. Comprueba que está activo:

  ```bash
  sudo systemctl status ahhh-certbot-renew.timer
  ```

- Los certificados viven en `/etc/letsencrypt` (host) y se montan de solo
  lectura en el contenedor nginx (`docker-compose.yml`). No se pierden al
  recrear contenedores.

## 8. Copias de seguridad

Hay dos mecanismos complementarios de copia de seguridad. Puedes usar uno,
el otro o ambos.

### 8.1 Completas con systemd timer (DB + media)

Copia de seguridad automatica (DB + media) mediante un timer systemd.
Requiere `AHHH_BACKUP_RETENTION_DAYS` en `.env` (por defecto 14).

```bash
sudo cp deploy/systemd/ahhh-backup.service /etc/systemd/system/
sudo cp deploy/systemd/ahhh-backup.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ahhh-backup.timer
sudo systemctl list-timers | grep ahhh   # comprobar la proxima ejecucion
```

Se ejecuta a diario a las 03:15 (+/-30 min) y genera:

- `backups/daily/db_ahhh_YYYY-MM-DD.sql.gz`: dump de PostgreSQL (con
  `--clean --if-exists`, autoclimpiable al restaurar).
- `backups/daily/media_ahhh_YYYY-MM-DD.tar.gz`: contenido del volumen de media.
- `backups/monthly/`: copia del dia 1 de cada mes (historico contable, no rota).

Rotacion: se borran los `db_`/`media_` diarios con mas de
`AHHH_BACKUP_RETENTION_DAYS` dias (por la fecha del nombre del archivo).

### 8.2 Solo PostgreSQL con cron (con copia off-site en Backblaze B2)

Este script hace un `pg_dump` del contenedor `ahhh_postgres`, lo comprime en
gzip y rota los dumps antiguos:

- **Script:** `deploy/backup_db.sh`
- **Cronjob:** `deploy/cron/ahhh_backup` (diario a las 03:00)

Instalacion (una vez):

```bash
chmod +x /opt/ahhh-ibiza/deploy/backup_db.sh
sudo cp /opt/ahhh-ibiza/deploy/cron/ahhh_backup /etc/cron.d/ahhh_backup
```

Los dumps quedan en `backups/ahhh_db_AAAA-MM-DD_HH-MM-SS.sql.gz`. Se conservan
los 14 mas recientes (`AHHH_BACKUP_KEEP` para cambiar). El log de cada ejecucion
queda en `backups/backup.log`.

Para que los backups sobrevivan a un fallo del propio servidor, se puede subir
cada dump a **Backblaze B2** (10 GB gratuitos). El script usa `rclone`:

```bash
sudo apt install -y rclone
rclone config   # elige "backblaze B2", pon tu Account ID y Application Key
rclone mkdir ahhh-b2:ahhh-ibiza-backups
```

Anade al `.env`:

```ini
AHHH_B2_REMOTE=ahhh-b2:ahhh-ibiza-backups
```

Con esto, cada ejecucion del cron sube tambien el dump a B2. El script hace
3 intentos de subida; si falla, aborta con error en el log y no borra el dump
local. Si no quieres copia remota, deja `AHHH_B2_REMOTE` sin definir.

Media (fotos y videos subidos): guarda el volumen `media_data`. Los archivos
se pueden copiar montando el volumen en un contenedor temporal o con la ruta
que exponga el volumen en el host (`docker volume inspect ahhh-ibiza_media_data`).
Programa las copias con `cron` y sacalas del servidor con el mismo `rclone`.

### 8.3 Ejecutar a mano

```bash
cd /opt/ahhh-ibiza
sudo ./deploy/backup.sh
```

### 8.4 Restauracion

`deploy/restore.sh` detiene app y nginx durante la restauracion y los reanuda
al terminar. Requiere confirmacion (escribe `RESTORE`) o `--yes` para saltarla.

```bash
cd /opt/ahhh-ibiza

# Base de datos (sobreescribe la actual; el dump hace DROP + recreate)
sudo ./deploy/restore.sh db backups/daily/db_ahhh_2026-01-01.sql.gz

# Media (sobreescribe el volumen de media)
sudo ./deploy/restore.sh media backups/daily/media_ahhh_2026-01-01.tar.gz
```

### 8.4 Saca las copias del servidor

La rotacion solo protege contra errores de datos, no contra fallos del disco o
del servidor. Programa la salida de `backups/` del servidor (scp, rclone o S3)
a otro sitio, p. ej. con cron diario:

```bash
rclone copy /opt/ahhh-ibiza/backups remote:ahhh-backups --include "*.gz"
```

## 9. Consumo diario de Tangas (planes de anuncios)

Cada anuncio con un plan de pago (`Destacado`, `Siempre arriba`) descuenta a su
propietario el `price_tangas` del plan **por día**. Si el saldo no alcanza, el
anuncio se degrada al plan Básico (sigue activo, sin promoción). El primer día
se cobra al elegir el plan en el formulario del anuncio; los siguientes los
cobra el timer diario.

### 9.1 Instalacion (produccion)

Requiere `AHHH_TANGAS_CHARGE_HOUR` en `.env` (formato `HH:MM`, por defecto
`02:45`). El instalador genera el timer de systemd con esa hora:

```bash
cd /opt/ahhh-ibiza
sudo ./deploy/install_charge_timer.sh
sudo systemctl list-timers | grep ahhh   # comprobar la proxima ejecucion
```

El timer corre a diario con retardo aleatorio de 30 min (`Persistent=true`:
si el servidor estaba apagado, se ejecuta al arrancar). No choca con el backup
(03:15) ni con la renovacion del certificado (04:30).

### 9.2 Ejecutar a mano y probar

```bash
# Previsualizar lo que haria hoy (no cambia nada)
sudo docker compose exec -T app python manage.py consume_plan_tangas --dry-run

# Cobrar ya
sudo docker compose exec -T app python manage.py consume_plan_tangas

# Simular para una fecha concreta
sudo docker compose exec -T app python manage.py consume_plan_tangas --dry-run --date 2026-08-20
```

El cobro es idempotente por anuncio y dia (`last_tangas_charged_at`): da igual
cuantas veces se ejecute el mismo dia, cada anuncio paga una sola vez.

### 9.3 Notas

- Cambiar de plan de pago a otro cobra el día completo del nuevo plan al guardar.
- Los anuncios ya promocionados antes de instalar el timer se cobran en la
  primera ejecución (sin retroactivo).

## 10. Notas importantes

- **Rate limiting**: para que `django-ratelimit` (5 intentos/h por IP en
  login/registros) funcione con varios workers, la cache usa Redis
  (`AHHH_REDIS_URL`). Sin Redis, cada worker contaría por separado.
- **IP real del cliente**: nginx envía `X-Forwarded-For` (ya configurado en
  `deploy/nginx/ahhh.conf`). Sin eso, todo el tráfico parecería venir de la
  misma IP y el rate limiting compartiría el contador.
- **HTTPS**: con `AHHH_DEBUG=false` Django activa cookies seguras y HSTS, y
  nginx ya redirige el puerto 80 al 443 (`deploy/nginx/ahhh.conf`). Hasta que
  el certificado real esté activo, el sitio funciona con el temporal autofirmado
  pero el navegador mostrará una advertencia de seguridad (es esperable).
  No uses `AHHH_SECURE_SSL_REDIRECT=false` en producción: rompería la
  redirección HTTP→HTTPS a nivel de Django.
- **Renovación del certificado**: la gestiona el timer
  `ahhh-certbot-renew` (diario, solo renueva cerca de la caducidad). Revisa
  `sudo systemctl status ahhh-certbot-renew.timer` tras desplegar.
- **Subida de archivos**: `client_max_body_size 40m` en nginx permite subir
  imágenes/videos dentro de la cuota de 35 MB por perfil.
- **Logs**:

```bash
sudo docker compose logs -f app
sudo docker compose logs -f nginx
```

## 11. Referencia: sin Docker (alternativa manual)

La versión anterior de esta guía desplegaba Django con gunicorn instalado en
el host, nginx del sistema y solo PostgreSQL en Docker. Es viable pero tiene
más piezas que mantener. Si prefieres esa ruta, los puntos relevantes eran:
gunicorn `core.wsgi:application` con `--bind 127.0.0.1:8000 --workers 3`,
nginx del host sirviendo `/static/` y `/media/`, y la base en el contenedor
`db` expuesta en `127.0.0.1:5432`.
