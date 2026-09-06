# Ahhh! Ibiza

Marketplace/directorio adulto para profesionales y usuarios registrados.

- Los visitantes ven contenido publico.
- Los usuarios registrados desbloquean contenido privado/HOT.
- Los profesionales gestionan su perfil, anuncios, media y saldo de Tangas.
- El superusuario (staff) administra todo desde el panel de control `/control/` (y el admin de Django en `/admin/`): gestiona profesionales, clientes, anuncios, media, movimientos de saldo, servicios, promociones, configuracion del sitio y la papelera (moderacion y restauracion). Tambien puede hacer recargas manuales de Tangas y configurar los paquetes de Tangas que los profesionales compran online.

## Stack

| Capa       | Tecnologia                          |
| ---------- | ----------------------------------- |
| Lenguaje   | Python 3.13                         |
| Framework  | Django 6.0.7                        |
| Base datos | PostgreSQL 16 (Docker Compose) |
| Media      | Imagenes de usuario (`media/`)      |
| Estaticos  | CSS/JS/imagenes base (`static/`)    |

## Estructura del proyecto

```
apps/
  accounts/   usuarios, perfiles, registro, dashboard profesional
  ads/        anuncios, servicios, galerias publica/HOT
  payments/   saldo de Tangas, paquetes, recarga online y pasarela de pago
core/         settings, urls y vista home
templates/    plantillas Django
static/       CSS, JS e imagenes base
media/        archivos subidos por usuarios (no versionado)
maintenance/  scripts internos de mantenimiento
launchers/    accesos rapidos .bat (Windows)
docs/         documentacion viva del proyecto
```

## Requisitos

- Python 3.13
- Git
- Docker Desktop (para la base de datos PostgreSQL)

## Instalacion y desarrollo local

```powershell
# 1. Clonar y entrar al proyecto
git clone <url-repo>
cd WEBPP

# 2. Crear y activar el entorno virtual (el venv NO se comparte)
python -m venv venv
venv\Scripts\activate

# 3. Instalar dependencias versionadas
pip install -r requirements.txt

# 4. Crear el archivo de entorno a partir de la plantilla
copy .env.example .env
#   Edita .env si necesitas valores distintos (ALLOWED_HOSTS, etc.)

# 5. Levantar PostgreSQL (Docker) y aplicar migraciones
docker compose up -d db
python manage.py migrate

# 6. Crear el superusuario y arrancar el servidor
python manage.py init_admin
python manage.py runserver
```

> Paso 7 opcional — datos de ejemplo (idempotentes, no pisan ediciones): las categorias de servicio para anuncios y los paquetes de Tangas para probar la recarga online.

```powershell
python manage.py seed_service_tags
python manage.py seed_tangas_packages
```

> El superusuario se crea con `init_admin` (no `createsuperuser`) usando `AHHH_ADMIN_USERNAME`/`AHHH_ADMIN_PASSWORD` del `.env`; es idempotente. Más detalle en `docs/despliegue.md`.

El sitio quedara disponible en <http://localhost:8000/> y el admin en <http://localhost:8000/admin/>.

## Accesos rapidos (Windows)

En `launchers/`:
- `SETUP.bat` — crea el venv, instala dependencias y genera `.env` si no existe (primer uso o dev nuevo).
- `SMART_MIGRATE.bat` — hace backup de la DB y aplica migraciones (obligatorio la primera vez y tras cada `git pull`).
- `RUN_APP.bat` — arranca el servidor de desarrollo.
- `TAKE_SNAPSHOT.bat` — guarda un snapshot de la base de datos.
- `CLEAN_CACHE.bat` — limpia caches de Python.
- `VERIFY_PROJECT.bat` — verificacion del proyecto.
- `RUN_TAILSCALE.bat` — arranca Tailscale.

Orden recomendado para un dev nuevo o tras clonar: `SETUP.bat` → `SMART_MIGRATE.bat` → `RUN_APP.bat`. Si no levantas PostgreSQL (`docker compose up -d db`) o no aplicas las migraciones, la base de datos quedara vacia y las paginas fallaran con errores de conexion o tablas inexistentes.

## Variables de entorno (`.env`)

| Variable                  | Descripcion                                  | Default            |
| ------------------------- | -------------------------------------------- | ------------------ |
| `AHHH_DEBUG`              | `true` en local, `false` en produccion       | `true`             |
| `AHHH_SECRET_KEY`         | Clave secreta de Django                      | solo-valida-en-local |
| `AHHH_ALLOWED_HOSTS`      | Hosts permitidos, separados por comas        | `localhost,127.0.0.1,[::1],...` |
| `AHHH_TIME_ZONE`          | Zona horaria                                 | `Europe/Madrid`    |
| `AHHH_CSRF_TRUSTED_ORIGINS` | Origenes confiables CSRF (https)          | vacio              |
| `AHHH_SECURE_SSL_REDIRECT`  | Redireccion SSL en produccion             | `true` en prod     |
| `AHHH_SECURE_HSTS_SECONDS`  | Duración HSTS en produccion               | `3600` en prod     |
| `AHHH_POSTGRES_DB`          | Nombre de la base PostgreSQL              | `ahhh_db`          |
| `AHHH_POSTGRES_USER`        | Usuario de PostgreSQL                     | `ahhh_user`        |
| `AHHH_POSTGRES_PASSWORD`    | Password de PostgreSQL                    | (obligatorio)      |
| `AHHH_DB_HOST`              | Host de PostgreSQL                        | `127.0.0.1`        |
| `AHHH_DB_PORT`              | Puerto de PostgreSQL                      | `5432`             |
| `AHHH_ADMIN_USERNAME`       | Usuario superadmin (para `init_admin`)    | `Patricia`         |
| `AHHH_ADMIN_PASSWORD`       | Password del superadmin                   | (obligatorio)      |
| `AHHH_ADMIN_EMAIL`          | Correo del superadmin (init_admin se lo asigna, idempotente) | vacio |
| `AHHH_PAYMENT_GATEWAY`      | Pasarela de pago activa (`dummy` desarrollo, `disabled` prod sin pasarela) | `dummy`      |
| `AHHH_PAYMENT_MODE`         | Modo de la pasarela: `test` o `live`      | `test`             |
| `AHHH_NGINX_CONF`           | Archivo de config nginx (`ahhh.conf` HTTPS o `ahhh.http.conf` solo HTTP) | `ahhh.conf` |
| `AHHH_SESSION_COOKIE_SECURE`| Cookie session segura (solo HTTPS); `false` en despliegue HTTP temporal | `true` en prod |
| `AHHH_CSRF_COOKIE_SECURE`   | Cookie CSRF segura (solo HTTPS); `false` en despliegue HTTP temporal  | `true` en prod |
| `AHHH_PUBLIC_BASE_URL`      | Origen publico (sin barra final); base de la URL del webhook de pagos | vacio |
| `AHHH_EMAIL_HOST`           | Servidor SMTP de salida; vacio usa el backend de consola | vacio |
| `AHHH_EMAIL_PORT`           | Puerto del SMTP                              | `587`             |
| `AHHH_EMAIL_HOST_USER`      | Usuario del SMTP                             | vacio             |
| `AHHH_EMAIL_HOST_PASSWORD`  | Contraseña del SMTP                          | vacio             |
| `AHHH_EMAIL_USE_TLS`        | TLS para el SMTP (`true`/`false`)            | `true`            |
| `AHHH_DEFAULT_FROM_EMAIL`   | Remitente de los correos                     | `Ahhh! Ibiza <noreply@ahhh-ibiza.com>` |

`.env` esta en `.gitignore`: nunca se sube al repositorio. Solo se versiona `.env.example`. Las claves privadas de la pasarela real van solo en el `.env` (ver `docs/pagos_pasarela.md`).

## Produccion

El proyecto incluye un despliegue Docker completo (app + nginx + PostgreSQL + Redis)
pensado para que lo ejecute una persona sin experiencia en despliegues:

- `docker-compose.yml` orquesta los 4 servicios.
- `Dockerfile` construye la app (gunicorn).
- `deploy/` contiene `entrypoint.sh` (migrate + init_admin + collectstatic),
  `nginx/ahhh.conf` (proxy, static y media) y `systemd/ahhh.service`.
- `requirements/base.txt`, `requirements/dev.txt`, `requirements/prod.txt`.

Guia paso a paso en `docs/despliegue.md`.

Los profesionales compran Tangas online: la pasarela esta abstraida tras una
interfaz comun y en desarrollo usa `dummy` (no cobra nada). Pendiente elegir una
pasarela real adulto-friendly y conectar su webhook con firma en HTTPS.
Detalle y arquitectura en `docs/pagos_pasarela.md`.

Mas detalle en `docs/roadmap.md` (vision y fases maestras) y `docs/state_of_play.md` (estado actual del proyecto).

## Copias de seguridad de la base de datos

El proyecto incluye backup automatico de PostgreSQL, con opcion de copia off-site
en **Backblaze B2** (u otro destino compatible con rclone):

- `deploy/backup_db.sh` — script de backup: hace un `pg_dump` del contenedor
  `ahhh_postgres`, lo comprime en gzip, lo guarda en `backups/`, rota los dumps
  antiguos y (si esta configurado) lo sube a B2.
- `deploy/cron/ahhh_backup` — cronjob diario a las **03:00**.

Requiere docker en el PATH y el contenedor `ahhh_postgres` corriendo. Para la
copia off-site se necesita `rclone` instalado y un remote configurado (`rclone config`).

Instalacion en el servidor:

```bash
chmod +x /opt/ahhh-ibiza/deploy/backup_db.sh
sudo cp /opt/ahhh-ibiza/deploy/cron/ahhh_backup /etc/cron.d/ahhh_backup
```

Para activar la subida a Backblaze B2, anade al `.env`:

```ini
AHHH_B2_REMOTE=ahhh-b2:ahhh-ibiza-backups
```

Donde `ahhh-b2` es el remote de rclone hacia tu bucket y `ahhh-ibiza-backups` la
carpeta de destino. Guia completa en `docs/despliegue.md`.

## Documentacion

`docs/` es la fuente de verdad del estado del proyecto. Antes de tocar codigo, lee:

- `docs/roadmap.md`
- `docs/state_of_play.md`
- `docs/todo.md`
- `docs/pagos_pasarela.md` — pasarela de pago: arquitectura y como anadir una real
- `docs/handover_report.md` — reglas clave para contribuir (no ensuciar la raiz, actualizar docs, etc.)
