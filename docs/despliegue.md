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

- (Opcional, para HTTPS) un dominio apuntando al IP del servidor.

## 3. Archivos de despliegue (ya en el repo)

```
Dockerfile                 Imagen de la app (dependencias prod + entrypoint)
.dockerignore              Excluye venv, media, .env, .git del build
deploy/entrypoint.sh       migrate + init_admin + collectstatic + gunicorn
deploy/nginx/ahhh.conf     Configuracion de nginx (proxy, static, media)
deploy/systemd/ahhh.service  Unidad systemd que arranca/para el stack
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
AHHH_POSTGRES_DB=ahhh_db
AHHH_POSTGRES_USER=ahhh_user
AHHH_POSTGRES_PASSWORD=<contraseña segura de la base de datos>
AHHH_ADMIN_USERNAME=Patricia
AHHH_ADMIN_PASSWORD=<contraseña del superadmin>
AHHH_AUTH_RATE=5/h
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
- El `.env` no debe versionarse ni compartirse.

### 4.3 Arrancar el stack

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

### 4.4 Verificar

```bash
curl http://localhost/health/
# -> {"status": "ok"}
```

Abre `http://tu-dominio.com` en el navegador y entra en `/admin/` con el
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

## 7. HTTPS con Let's Encrypt (certbot)

Con nginx en Docker hay dos opciones. La sencilla es añadir un `server`
443 al config de nginx y renovar manualmente con certbot en el host:

```bash
sudo apt install -y certbot
sudo certbot certonly --standalone -d tu-dominio.com -d www.tu-dominio.com
```

Después añade el bloque HTTPS a `deploy/nginx/ahhh.conf` (ssl_certificate
apuntando a `/etc/letsencrypt/live/tu-dominio.com/`), redirige el puerto 80 al
443 y vuelve a levantar nginx:

```bash
sudo docker compose up -d nginx
```

Para renovación automática, un timer de systemd que ejecute
`certbot renew` y luego `docker compose exec nginx nginx -s reload`.

## 8. Copias de seguridad

Base de datos:

```bash
cd /opt/ahhh-ibiza
sudo docker compose exec -T db pg_dump -U ahhh_user ahhh_db > backups/ahhh_$(date +%F).sql
```

Media (fotos y videos subidos): guarda el volumen `media_data`. Los archivos
se pueden copiar montando el volumen en un contenedor temporal o con la ruta
que exponga el volumen en el host (`docker volume inspect ahhh-ibiza_media_data`).

Programa las copias con `cron` y sácalas del servidor (scp/rclone/S3).

## 9. Notas importantes

- **Rate limiting**: para que `django-ratelimit` (5 intentos/h por IP en
  login/registros) funcione con varios workers, la cache usa Redis
  (`AHHH_REDIS_URL`). Sin Redis, cada worker contaría por separado.
- **IP real del cliente**: nginx envía `X-Forwarded-For` (ya configurado en
  `deploy/nginx/ahhh.conf`). Sin eso, todo el tráfico parecería venir de la
  misma IP y el rate limiting compartiría el contador.
- **HTTPS**: con `AHHH_DEBUG=false` Django activa cookies seguras, HSTS y
  redirección a HTTPS. Si pruebas sin dominio/certificado, usa
  `AHHH_SECURE_SSL_REDIRECT=false` mientras tanto.
- **Subida de archivos**: `client_max_body_size 40m` en nginx permite subir
  imágenes/videos dentro de la cuota de 35 MB por perfil.
- **Logs**:

```bash
sudo docker compose logs -f app
sudo docker compose logs -f nginx
```

## 10. Referencia: sin Docker (alternativa manual)

La versión anterior de esta guía desplegaba Django con gunicorn instalado en
el host, nginx del sistema y solo PostgreSQL en Docker. Es viable pero tiene
más piezas que mantener. Si prefieres esa ruta, los puntos relevantes eran:
gunicorn `core.wsgi:application` con `--bind 127.0.0.1:8000 --workers 3`,
nginx del host sirviendo `/static/` y `/media/`, y la base en el contenedor
`db` expuesta en `127.0.0.1:5432`.
