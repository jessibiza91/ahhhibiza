# Auditoria de Producto y UX - 2026-06-20

Este documento resume el repaso de objetivos, estado real del sistema, orden tecnico y experiencia mobile-first.

Nota de seguimiento: los riesgos corregidos desde esta auditoria se registran en
`docs/consolidation_route_map_2026-07-05.md`. Este archivo conserva el diagnostico
original como referencia historica.

## Objetivo del Proyecto

Ahhh! Ibiza debe ser una plataforma visual y sencilla para tres tipos de uso:

- Visitante/cliente: descubrir perfiles, registrarse, ver contenido HOT, guardar favoritas, crear un perfil privado y contactar.
- Profesional: crear y mantener perfil/anuncios desde movil, subir material, elegir promocion en Tangas y ver clientes que la marcaron como favorita.
- Patricia/superadmin: controlar usuarios, perfiles, anuncios, galerias, Tangas, papelera, promociones y moderacion sin depender del Django Admin.

El principio clave sigue siendo mobile-first: la web se visitara y gestionara sobre todo desde telefono o tablet.

## Lo que Existe Realmente

- Django 6 con apps separadas: `accounts`, `ads`, `payments`, `core`.
- Registro/login por rol.
- Panel cliente en `/accounts/cliente/`.
- Perfil privado de cliente en `/accounts/perfil/editar/`, reutilizando `Profile` y `ProfileMedia`.
- Favoritos con `FavoriteAd`.
- Panel profesional en `/accounts/dashboard/`.
- Vista profesional de clientes que marcaron favoritos en `/accounts/dashboard/clientes-favoritos/`.
- Anuncios con capa publica y capa HOT.
- Productos de promocion con precio interno en Tangas y prioridad.
- Panel visual superadmin en `/accounts/control/`.
- Vistas superadmin para profesionales, clientes, fichas de usuario, anuncios, promociones y papelera.
- Papelera para usuarios, anuncios, media de perfil e imagenes de anuncio.
- Lanzadores `.bat` concentrados en `launchers/`.
- Documentacion viva en `docs/`.

## Lo que Esta Bien Encaminado

- La idea de producto ya esta clara y coherente.
- La estructura por apps/directorios es razonable.
- La mayor parte de la experiencia diaria ya evita el Django Admin.
- Las pantallas usan tarjetas, miniaturas, botones grandes e iconos.
- El flujo cliente-profesional gana confianza con perfil privado de cliente.
- Patricia tiene herramientas reales de intervencion directa.
- Los Tangas ya estan bien conceptualizados como moneda interna profesional.
- Las vistas principales renderizan correctamente con el cliente de Django.

## Riesgos y Deudas Detectadas

### Permisos

- `/crear/` permite acceso a cualquier usuario autenticado. Un cliente no tiene boton visible, pero puede abrir la URL manualmente.
- Patricia tambien puede abrir `/crear/`, aunque su flujo correcto deberia ser crear anuncios desde la ficha de usuario.
- `ad_delete`, `delete_ad_image` y `delete_profile_media` siguen aceptando acciones destructivas por GET/fetch sin exigir POST+CSRF de forma clara.

### UX Mobile

- La navegacion superior puede saturarse en telefono: logo, soporte, panel, perfil, salir y otros botones compiten en una fila.
- El detalle de anuncio aun no tiene contacto sticky inferior para movil.
- Formularios largos como perfil, anuncio y ficha superadmin funcionan, pero pueden cansar en telefono.
- La ficha superadmin de usuario ya es potente, pero demasiado densa; necesita tabs o secciones plegables.
- Algunas acciones importantes dependen de `confirm()` del navegador, que es brusco y poco elegante.

### Orden y Mantenibilidad

- `templates/dashboard/control_user_detail.html`, `control_ad_detail.html`, `ad_form.html` y `profile_form.html` son plantillas muy grandes.
- Conviene extraer componentes parciales para tarjetas de media, bloques de contacto, botones de accion y cabeceras.
- Hay dos entornos virtuales en raiz: `venv` y `.venv`. El proyecto deberia escoger uno.
- `seed_tags.py` sigue en la raiz; deberia moverse a `maintenance/` o convertirse en management command.
- `maintenance/` contiene logs y capturas de navegador; deberian ir a `maintenance/logs/` o `artifacts/`.
- `launchers/CLEAN_CACHE.bat` no respeta las exclusiones seguras que si tiene `maintenance/clean_structure.py`.
- `state_of_play.md` conserva fecha antigua y notas historicas mezcladas con estado actual.

### Producto Pendiente

- Buscador real por texto/zona/servicios.
- Filtros visibles en home.
- Consumo real de Tangas al activar/renovar promociones.
- Caducidad de promociones por duracion.
- Estados de pago/suscripcion profesional.
- Rutina `cleanup_professionals --dry-run`.
- Auditoria/log de moderacion.
- Restaurar desde papelera.
- Preparacion de produccion: settings por entorno, secretos, `DEBUG=False`, `ALLOWED_HOSTS` real.

## Diagnostico por Rol

### Cliente

Estado: bastante bien encaminado.

Fortalezas:
- Panel propio.
- Favoritas.
- Acceso HOT registrado.
- Perfil privado con galeria.
- Mensaje de privacidad claro.

Mejoras prioritarias:
- Hacer el perfil privado aun mas corto y guiado en movil.
- Mejorar buscador/filtros.
- Contacto sticky en detalle.
- Mensajes visuales tras guardar/quitar favorito.

### Profesional

Estado: funcional y visual, pero faltan cierres operativos.

Fortalezas:
- Dashboard con checklist.
- Anuncios en tarjetas.
- Editor de perfil y anuncio visual.
- Galeria con miniaturas.
- Vista de clientes que la marcaron como favorita.

Mejoras prioritarias:
- Restringir creacion de anuncios solo a profesionales.
- Hacer alta inicial tipo asistente paso a paso.
- Estados de subida: subiendo, subido, error, cuota superada.
- Consumo/caducidad real de Tangas.
- Explicar mejor renovacion y visibilidad.

### Patricia / Superadmin

Estado: potente, pero necesita bajar complejidad visual.

Fortalezas:
- Panel visual.
- Listado profesionales/clientes.
- Ficha de intervencion.
- Edicion visual de anuncios.
- Galerias y papelera.
- Promociones y recarga Tangas.

Mejoras prioritarias:
- Tabs en ficha de usuario: Resumen, Perfil, Galeria, Anuncios/Favoritas, Finanzas, Moderacion.
- Sustituir enlaces Django por acciones visuales propias cuando sea posible.
- Auditoria de acciones.
- Suspender/reactivar usuario sin enviarlo a papelera.
- Vista clara de almacenamiento por usuario.

## Prioridad Recomendada

1. Cerrar permisos y metodos destructivos: anuncios solo profesionales, borrados por POST+CSRF.
2. Mejorar navegacion movil: menu compacto/hamburguesa o barra inferior por rol.
3. Contacto sticky en detalle de anuncio movil.
4. Dividir ficha superadmin y formularios largos en tabs/secciones plegables.
5. Orden tecnico: un solo virtualenv, mover `seed_tags.py`, proteger `CLEAN_CACHE.bat`, ordenar logs/capturas.
6. Buscador/filtros reales.
7. Tangas real: consumo, caducidad, renovacion y estado de pago.
8. Limpieza segura con `--dry-run` y launcher.

## Verificaciones Realizadas

- `python manage.py check` sin errores.
- Rutas principales renderizadas con Django Client por rol.
- Confirmado que cliente y Patricia pueden acceder a `/crear/`, lo que debe corregirse.
- Confirmado que el panel cliente, perfil cliente, panel profesional, vista de clientes favoritos y paneles superadmin renderizan.
- No se pudo usar navegador integrado por error interno de la sesion; queda pendiente revision visual real con capturas movil/tablet.
