# Roadmap Maestro - Ahhh! Ibiza

Este documento es la referencia viva para saber que estamos haciendo, por que lo hacemos y en que punto esta el proyecto.

Route map operativo UX/lanzamiento: `docs/ux_launch_route_map.md`.
Auditoria de producto y UX: `docs/ux_product_audit_2026-06-20.md`.
Auditoria de cableado y flujos: `docs/cableado_flows_audit_2026-06-20.md`.
Routemap de consolidacion activo: `docs/consolidation_route_map_2026-07-05.md`.
Auditoria de rutas administrativas: `docs/admin_route_audit_2026-07-05.md`.
Auditoria de rutas cliente/profesional: `docs/user_role_route_audit_2026-07-05.md`.
Pasarela de pago: `docs/pagos_pasarela.md`.

## Vision del Producto

Ahhh! Ibiza es una plataforma privada para conectar profesionales y usuarios registrados.

- Los profesionales tienen un perfil, saldo operativo y uno o varios anuncios.
- Cada anuncio tiene una capa publica visible para visitantes y una capa privada/HOT visible solo para usuarios registrados.
- La plataforma asigna espacio de almacenamiento a cada profesional para imagenes y videos.
- El sistema debe liberar espacio eliminando o archivando profesionales que no usen la plataforma o que no paguen el servicio durante un periodo configurable.

## Principios del Proyecto

1. **Documentacion al dia**: cualquier cambio importante debe actualizar `docs/`.
2. **Orden por directorios**: la raiz debe quedar limpia; scripts en `maintenance/`, lanzadores en `launchers/`, logica en `apps/`, plantillas en `templates/`.
3. **Lanzadores centralizados**: las operaciones frecuentes deben tener `.bat` dentro de `launchers/`.
4. **Base de datos unica**: PostgreSQL 16 vía Docker Compose (`docker-compose.yml`, servicio `db`).
5. **Media aislada por usuario**: los archivos de usuario deben vivir bajo `media/user_{id}/` siempre que sea posible.
6. **Borrado con intencion**: toda eliminacion fisica de media debe estar validada por propietario, registro de motivo o rutina operativa clara.
7. **Mobile first**: las pantallas criticas deben funcionar comodamente en movil.
8. **Superadmin fuerte**: la administracion debe poder controlar usuarios, perfiles, anuncios, materiales, pagos y limpieza sin tocar codigo.

## Estado Actual Resumido

El proyecto ya contiene:

- Django 6 con usuario custom.
- Apps principales: `accounts`, `ads`, `payments`.
- Registro/login para clientes y profesionales.
- Perfil profesional con avatar, bio, zona, origen, redes y galeria.
- Anuncios con descripcion publica, descripcion HOT, tags de servicios, promocion interna en Tangas y galeria publica/privada.
- Panel cliente registrado con favoritas y perfiles activos.
- Dashboard profesional basico.
- Compra online de Tangas con pasarela simulada (dummy) y webhook idempotente.
- Age gate y estilo visual base.
- Backups y lanzadores operativos.

Problemas detectados antes del lanzamiento y estado actual:

- Corregido: `manage.py check` pasa sin errores.
- Corregido: las plantillas usan `ad.cover_image` en vez de `ad.image`.
- Corregido: la ruta `delete_ad_image` esta conectada en `apps/ads/urls.py`.
- Corregido: el dashboard usa estados actuales (`ACTIVE`, `CERRADO`).
- Corregido: se retiro la logica temporal para un usuario concreto.
- Corregido: settings configurables por entorno, zona horaria local y protecciones HTTPS al desactivar `DEBUG`.
- Corregido: filtros de portada por texto y zona; se retiro el selector de categoria.
- Implementado: recarga online de Tangas con pasarela simulada (dummy); queda conectar una pasarela real adulto-friendly con webhook HTTPS firmado.
- Validado: contratos autenticados criticos cubiertos por tests; queda revision visual de formularios con sesion.

## Fase 1 - Estabilizacion Tecnica

Objetivo: que el proyecto arranque, se pueda verificar y no tenga rutas rotas.

- Resolver bloqueo de `manage.py check` / `django.setup()`.
- Corregir imagen principal de anuncio usando la primera imagen publica de `ad.gallery`.
- Conectar ruta para borrar imagenes de anuncios.
- Ajustar dashboard a estados reales.
- Revisar URLs y enlaces muertos (`href="#"`, acciones no conectadas).
- Eliminar o aislar logica temporal de usuarios de prueba.
- Confirmar que las migraciones no se borran por rutinas de limpieza ordinarias.

Entrega esperada:

- `manage.py check` funcionando.
- Flujo profesional minimo operativo: registro/login, editar perfil, crear anuncio, ver anuncio, editar anuncio, borrar media.
- Documentacion actualizada.

## Fase 2 - Producto Minimo Lanzable

Objetivo: lanzar una experiencia completa y comprensible.

- Home con feed real de anuncios activos.
- Panel cliente para volver a perfiles favoritos y descubrir perfiles activos.
- Buscador sencillo por zona y texto publico.
- Detalle de anuncio con galeria publica y privada funcional.
- Favoritos de cliente para guardar/quitar profesionales desde home, detalle y panel.
- Contacto real por WhatsApp/Telegram/redes desde datos del profesional.
- Contacto directo por llamada, WhatsApp y Telegram desde datos del profesional.
- Dashboard profesional con estado claro de anuncios, media, visitas y cuota.
- Dashboard profesional con checklist de activacion y siguiente accion recomendada.
- Experiencia mobile-first para cliente y profesional.
- Mensajes de error/confirmacion visibles para acciones importantes.
- Textos legales y protocolo de seguridad revisados.

Entrega esperada:

- Plataforma usable por un profesional real y un usuario registrado.
- Navegacion sin enlaces muertos.
- Experiencia movil revisada.

## Fase 3 - Cuotas, Pagos y Retencion

Objetivo: controlar el uso de almacenamiento y liberar espacio de manera automatica.

Los Tangas son saldo interno del profesional. No son un precio publico, no aparecen en fichas ni detalles para clientes, y sirven para recargar la cuenta profesional, renovar anuncios y consumir promocion/prioridad dentro de la plataforma.

### Compra online de Tangas (implementada, con pasarela simulada)

El flujo de compra esta construido y probado, pero con la pasarela `dummy`:
solo cobra de verdad cuando se conecte una pasarela real.

- Los profesionales eligen un paquete en su cartera y se crea una orden PENDING.
- La pasarela (via contrato `BaseGateway`) devuelve una URL de pago.
- El webhook `/pagos/webhook/` verifica firma, importe y moneda, y acredita el
  saldo de forma atomica e idempotente (con `select_for_update`).
- Superadmin gestiona los paquetes (crear, editar, desactivar) desde el panel y
  desde Django Admin; ordenes y logs de webhook quedan registrados.
- `AHHH_PAYMENT_GATEWAY` (dummy) y `AHHH_PAYMENT_MODE` (test/live) se configuran
  por entorno. `dummy` esta bloqueada en produccion.

Pendiente: elegir una pasarela adulto-friendly y conectar su webhook con firma
en HTTPS. Detalle completo en `docs/pagos_pasarela.md`.

### Politica de Profesionales Inactivos

Campos o configuracion recomendada:

- `last_seen_at`: ultima actividad real.
- `subscription_status`: `ACTIVE`, `PAST_DUE`, `GRACE`, `SUSPENDED`, `DELETED`.
- `paid_until`: fecha hasta la que el profesional tiene servicio pagado.
- `storage_limit_mb`: cuota asignada.
- `scheduled_deletion_at`: fecha prevista de eliminacion si no regulariza.

Rutina recomendada:

1. Marcar como `PAST_DUE` si `paid_until` queda atras.
2. Aplicar periodo de gracia configurable.
3. Suspender visibilidad del perfil/anuncios si no paga.
4. Notificar antes de eliminar media o cuenta.
5. Eliminar fisicamente media y/o cuenta cuando expire el periodo de retencion.

Regla inicial sugerida:

- Profesionales sin pago: 7 dias de gracia, 30 dias suspendidos, eliminacion despues de 45 dias.
- Profesionales inactivos aunque pagados: aviso a los 60 dias, suspension opcional a los 90 dias si no hay actividad.
- Usuarios cliente inactivos: conservar salvo peticion legal o limpieza manual.

Entrega esperada:

- Comando de mantenimiento tipo `python manage.py cleanup_professionals`.
- Launcher `.bat` para auditoria o limpieza segura.
- Modo simulacion (`--dry-run`) antes de borrar nada.
- Log de lo eliminado o marcado.

## Fase 4 - Operacion y Backoffice

Objetivo: que Patricia/admin pueda controlar la plataforma sin tocar codigo.

- Panel de administracion mejorado para usuarios, perfiles, anuncios, pagos y media.
- Django Admin reforzado para usuarios, perfiles, anuncios, media, servicios y transacciones.
- Vista de profesionales por estado de pago, cuota usada y ultima actividad.
- Acciones administrativas: suspender, reactivar, ampliar cuota, borrar media, resetear password.
- Reportes basicos: altas, anuncios activos, uso de disco, ingresos, pendientes de pago.

## Fase 5 - Preparacion de Produccion

Objetivo: poder desplegar con seguridad.

- Variables de entorno para secretos.
- `DEBUG=False` fuera de local.
- `ALLOWED_HOSTS` real.
- Politica de backups.
- Configuracion de media/static.
- Revision legal minima para plataforma adulta.
- Pruebas de humo documentadas.

## Backlog Tecnico

- Revisar codificacion de textos antiguos con caracteres rotos.
- Convertir constantes de cuota a settings configurables.
- Evitar `except: pass` silenciosos en rutas criticas.
- Reemplazar endpoints destructivos GET por POST.
- Agregar tests para permisos de borrado y visibilidad privada.
- Separar settings de desarrollo/produccion.
- Revisar integridad de `maintenance/clean_structure.py`.

## Proxima Decision

Antes de lanzar, hay que decidir:

- Pasarela de pago real (adulto-friendly) y precio final de los paquetes de Tangas.
- Dominio y hosting objetivo (condiciona el webhook HTTPS de la pasarela).
- Periodo exacto de gracia para profesionales impagados.
- Si se elimina la cuenta completa o solo media/anuncios tras impago.
- Cuota inicial por profesional.
- Si los usuarios registrados ven todo el contenido HOT gratis o si habra capas de pago.
