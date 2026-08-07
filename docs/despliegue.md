# Despliegue - Ahhh! Ibiza

Notas para poner el proyecto en produccion detras de nginx.

## 1. Variables de entorno

Configura el `.env` siguiendo `.env.example`:

- `AHHH_DEBUG=false`
- `AHHH_ALLOWED_HOSTS=dominio.com,www.dominio.com`
- `AHHH_CSRF_TRUSTED_ORIGINS=https://dominio.com,https://www.dominio.com`
- `AHHH_SECRET_KEY=<clave fuerte>`
- `AHHH_AUTH_RATE=5/h` (rate limiting de login/registros)
- `AHHH_ADMIN_USERNAME=Patricia` y `AHHH_ADMIN_PASSWORD=<clave>` (superadmin inicial)

Con `AHHH_DEBUG=false`, Django activa cookies seguras, redireccion a HTTPS y HSTS.

## 2. Base de datos y superadmin

Levanta PostgreSQL con Docker:

```bash
docker compose up -d db
```

Aplica el esquema y crea el superadmin inicial (lee `AHHH_ADMIN_USERNAME`/`AHHH_ADMIN_PASSWORD` del `.env`):

```bash
python manage.py migrate
python manage.py init_admin
```

`init_admin` es idempotente: si el usuario ya existe, no hace nada.

## 3. Archivos estaticos

Django no sirve los estaticos en produccion. Hay que recogerlos una vez y tras cada cambio de CSS/JS:

```bash
python manage.py collectstatic --noinput
```

Se vuelcan en `STATIC_ROOT` (`staticfiles/` en la raiz del proyecto).

## 4. Archivos de media

Los subidos por usuarios (avatares, imagenes y videos de anuncios, media de perfil)
viven en `MEDIA_ROOT` (`media/`). nginx los sirve directamente; Django solo los usa
en desarrollo (`DEBUG=True`).

El proceso de la aplicacion necesita permiso de escritura sobre `media/`
y el proceso de nginx permiso de lectura.

## 5. nginx

Configuracion de referencia. Sustituye `dominio.com` y los puertos por los tuyos:

```nginx
server {
    listen 80;
    server_name dominio.com www.dominio.com;

    location /static/ {
        alias /var/www/ahhh-ibiza/staticfiles/;
    }

    location /media/ {
        alias /var/www/ahhh-ibiza/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Notas:

- `proxy_set_header X-Forwarded-For` es imprescindible para que el rate limiting por IP
  (`key='ip'` en login/registros) vea la IP real del cliente y no la de nginx. Si no,
  todo el trafico parecera venir de `127.0.0.1` y se compartiria el contador.
- Para HTTPS usa un `server` en el puerto 443 con certificado (Let's Encrypt) y redirige el 80 al 443.

## 6. Gunicorn (referencia)

```bash
gunicorn core.wsgi:application --bind 127.0.0.1:8000 --workers 3
```

## 7. Cache del rate limiting (Redis)

En desarrollo el rate limiting usa el cache `locmem`, que es **por proceso**.
Con varios workers de gunicorn cada worker tiene su propio contador y el limite
`5/h` se multiplicaria por el numero de workers.

Para un limite real y compartido entre todos los workers hay que usar un cache
central (Redis). En `settings.py`:

```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.getenv('AHHH_REDIS_URL', 'redis://127.0.0.1:6379/1'),
    },
}
```

y en `.env` / `.env.example`:

```ini
AHHH_REDIS_URL=redis://127.0.0.1:6379/1
```

Pendiente: instalar la dependencia (`pip install redis`) y levantar el contenedor
de Redis en produccion


