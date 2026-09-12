# Handover Report

## Para Futuros Agentes

Este proyecto sigue una estructura maestra. No cambiar la organizacion sin actualizar `docs/`.

Relacion de documentos: `docs/README.md` (indice).
Referencia de produccion y despliegue: `docs/despliegue.md`.
Referencia principal: `docs/roadmap.md`.

## Reglas Clave

1. **Leer documentacion primero**: empezar por `docs/README.md`, `docs/roadmap.md`, `docs/state_of_play.md` y `docs/todo.md`.
2. **Lanzadores centralizados**: las operaciones frecuentes deben vivir en `launchers/`.
3. **Base de datos**: PostgreSQL 16 vía Docker Compose (`docker compose up -d db`); superadmin con `manage.py init_admin`.
4. **No ensuciar la raiz**: nuevos scripts en `maintenance/`, documentacion en `docs/`, logica de negocio en `apps/`.
5. **Media por usuario**: mantener archivos de usuario bajo `media/user_{id}/` cuando aplique.
6. **Borrado fisico con cuidado**: toda eliminacion debe validar propietario y, para rutinas masivas, tener modo simulacion.
7. **Actualizar docs al cerrar cambios**: cada hito debe reflejarse en `docs/todo.md` y `docs/state_of_play.md`.

## Estructura Actual

- `apps/accounts`: usuarios, perfiles, registro, dashboard profesional.
- `apps/ads`: anuncios, servicios, galerias publica/HOT.
- `apps/payments`: transacciones basicas.
- `core`: settings, urls y home.
- `templates`: plantillas Django.
- `static`: CSS, JS e imagenes base.
- `media`: archivos subidos.
- `maintenance`: scripts internos.
- `launchers`: `.bat` de ejecucion y mantenimiento.
- `docs`: fuente de verdad del estado del proyecto (`README.md` es el indice; `archivo/` conserva notas historicas).
- `deploy/`: despliegue Docker (nginx, entrypoint, certificados HTTPS, backups, timers).

## Contexto del Producto

Ahhh! Ibiza es un marketplace/directorio adulto para profesionales y usuarios registrados.

- Los visitantes ven contenido publico.
- Los usuarios registrados desbloquean contenido privado/HOT.
- Los profesionales gestionan perfil, anuncios, media y saldo.
- El sistema debe incorporar retencion y limpieza de profesionales inactivos o impagados para liberar espacio.

## Estado de Rutas Relevantes

- Home: `/`
- Login: `/accounts/login/`
- Registro: `/accounts/register/`
- Dashboard profesional: `/accounts/dashboard/`
- Editar perfil: `/accounts/perfil/editar/`
- Crear anuncio: `/crear/`
- Detalle anuncio: `/<ad_id>/`
- Editar anuncio: `/anuncio/editar/<pk>/`
- Eliminar anuncio: `/anuncio/eliminar/<pk>/`

## Advertencias Tecnicas Actuales

- `manage.py check` pasa sin errores en la ultima revision.
- Las plantillas principales usan `ad.cover_image` para portada de anuncio.
- La ruta de borrado de imagenes de anuncio esta conectada en `apps/ads/urls.py`.
- `maintenance/clean_structure.py` solo borra caches Python; no borra migraciones.
- El sitio esta en produccion (https://ahibiza.com) con HTTPS real de Let's Encrypt y renovacion automatica. El dominio real es `ahibiza.com` (con una h); los ejemplos de la documentacion usan `ahhh-ibiza.com`/`tu-dominio.com` y hay que ajustarlos al dominio propio en el `.env` y en `deploy/nginx/ahhh.conf`.
- La pasarela de pagos esta en `disabled`: la recarga online bloqueada hasta integrar una pasarela real (ver `docs/pagos_pasarela.md`).
