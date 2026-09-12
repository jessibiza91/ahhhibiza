# Auditoria de Cableado y Flujos - 2026-06-20

Revision orientada a confirmar que rutas, permisos, formularios y acciones principales estan conectados.

Seguimiento: la suite automatizada y las mejoras posteriores se documentan en
`docs/consolidation_route_map_2026-07-05.md`.

## Verificaciones Automaticas

- `python manage.py check`: sin errores.
- `python manage.py makemigrations --check --dry-run`: sin cambios pendientes.
- Extraccion de nombres `{% url %}` y `redirect(...)`: 124 referencias, 0 nombres de ruta inexistentes.
- Usuarios temporales de auditoria eliminados al terminar.

## Flujos Probados

### Cliente

- Login cliente.
- Panel cliente `/accounts/cliente/`.
- Edicion de perfil privado `/accounts/perfil/editar/`.
- Persistencia de bio/datos de perfil.
- Marcar favorita.
- Ver detalle de anuncio con HOT desbloqueado.
- Intento de acceder a `/crear/`: redirige correctamente a panel cliente.

### Profesional

- Login profesional.
- Panel profesional `/accounts/dashboard/`.
- Edicion de perfil profesional.
- Crear anuncio.
- Editar anuncio.
- Ver detalle propio.
- Ver clientes que marcaron sus anuncios como favoritos.
- Borrado de anuncio por GET rechazado con 405.
- Borrado de anuncio por POST aceptado y enviado a papelera.

### Superadmin

- Login Patricia.
- Panel `/accounts/control/`.
- Profesionales `/accounts/control/profesionales/`.
- Clientes `/accounts/control/clientes/`.
- Papelera `/accounts/control/papelera/`.
- Promociones `/control/promociones/`.
- Ficha de cliente.
- Ficha de anuncio.

### Media

- Retirada de media de perfil por GET rechazada con 405.
- Retirada de media de perfil por POST aceptada y enviada a papelera.
- Retirada de imagen de anuncio por GET rechazada con 405.
- Retirada de imagen de anuncio por POST aceptada y enviada a papelera.

## Correcciones Aplicadas

- `/crear/` queda restringido a profesionales.
- Edicion y borrado de anuncios por rutas profesionales quedan restringidos a profesionales.
- `ad_delete` exige POST.
- `delete_ad_image` exige POST.
- `delete_profile_media` exige POST.
- Plantillas actualizadas para usar POST+CSRF en retiradas de media.
- Boton de borrar anuncio del dashboard profesional convertido de enlace GET a formulario POST.
- Textos de confirmacion ajustados: retirar/enviar a papelera en lugar de "permanente".

## Estado

Cableado principal correcto tras las correcciones. Quedan pendientes mejoras de UX, no roturas funcionales detectadas en esta pasada:

- Sustituir `confirm()` por modales visuales propios.
- Crear tests automatizados permanentes para estos flujos.
- Revision visual real en movil/tablet con navegador/capturas.
