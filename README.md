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
| `AHHH_PAYMENT_GATEWAY`      | Pasarela de pago activa (`dummy` en desarrollo) | `dummy`      |
| `AHHH_PAYMENT_MODE`         | Modo de la pasarela: `test` o `live`      | `test`             |

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

## Documentacion

`docs/` es la fuente de verdad del estado del proyecto. Antes de tocar codigo, lee:

- `docs/roadmap.md`
- `docs/state_of_play.md`
- `docs/todo.md`
- `docs/pagos_pasarela.md` — pasarela de pago: arquitectura y como anadir una real
- `docs/handover_report.md` — reglas clave para contribuir (no ensuciar la raiz, actualizar docs, etc.)
