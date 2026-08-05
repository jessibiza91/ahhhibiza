# Ahhh! Ibiza

Marketplace/directorio adulto para profesionales y usuarios registrados.

- Los visitantes ven contenido publico.
- Los usuarios registrados desbloquean contenido privado/HOT.
- Los profesionales gestionan su perfil, anuncios, media y saldo de Tangas.
- El superusuario (staff) administra todo desde el panel de control `/control/` (y el admin de Django en `/admin/`): gestiona profesionales, clientes, anuncios, media, movimientos de saldo, servicios, promociones, configuracion del sitio y la papelera (moderacion y restauracion). Tambien puede hacer recargas manuales de Tangas.

## Stack

| Capa       | Tecnologia                          |
| ---------- | ----------------------------------- |
| Lenguaje   | Python 3.13                         |
| Framework  | Django 6.0.7                        |
| Base datos | SQLite (`db_ahhh.sqlite3`) en local |
| Media      | Imagenes de usuario (`media/`)      |
| Estaticos  | CSS/JS/imagenes base (`static/`)    |

## Estructura del proyecto

```
apps/
  accounts/   usuarios, perfiles, registro, dashboard profesional
  ads/        anuncios, servicios, galerias publica/HOT
  payments/   transacciones y saldo de Tangas
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

# 5. Aplicar migraciones y crear el superusuario
python manage.py migrate
python manage.py createsuperuser

# 6. Arrancar el servidor de desarrollo
python manage.py runserver
```

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

Orden recomendado para un dev nuevo o tras clonar: `SETUP.bat` → `SMART_MIGRATE.bat` → `RUN_APP.bat`. Si no aplicas las migraciones, la base de datos quedara vacia y las paginas fallaran con errores de "no such table".

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

`.env` esta en `.gitignore`: nunca se sube al repositorio. Solo se versiona `.env.example`.

## Produccion

El proyecto es actualmente un prototipo local (SQLite, sin pagos desplegados). La migracion a produccion sigue pendiente y se abordara cuando se definan las reglas de negocio de Tangas y pagos.

Resumen de la ruta prevista:

1. Dividir `requirements.txt` en base/dev/prod y fijar versiones.
2. Migrar la base de datos a PostgreSQL (SQLite solo en local).
3. Preparar hosting, dominio, HTTPS, static/media y backups restaurables.
4. Integrar una pasarela de pago (aun no definida) para la compra de Tangas.

Mas detalle en `docs/roadmap.md` (vision y fases maestras) y `docs/state_of_play.md` (estado actual del proyecto).

## Documentacion

`docs/` es la fuente de verdad del estado del proyecto. Antes de tocar codigo, lee:

- `docs/roadmap.md`
- `docs/state_of_play.md`
- `docs/todo.md`
- `docs/handover_report.md` — reglas clave para contribuir (no ensuciar la raiz, actualizar docs, etc.)
