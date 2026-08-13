# Tareas del Proyecto "Ahhh! Ibiza"

Ver tambien: `docs/roadmap.md`.
Route map UX: `docs/ux_launch_route_map.md`.
Journeys UX: `docs/ux_user_journeys.md`.
Routemap de consolidacion: `docs/consolidation_route_map_2026-07-05.md`.

## Completado

- [x] Estructura base Django.
- [x] Base de datos: PostgreSQL 16 vía Docker Compose (migrado desde SQLite).
- [x] Apps segmentadas: `accounts`, `ads`, `payments`.
- [x] Registro/login para clientes y profesionales.
- [x] Panel visual para cliente registrado con favoritos.
- [x] Perfil privado para cliente con datos opcionales y subida de fotografias.
- [x] Dashboard profesional inicial.
- [x] Perfil profesional con avatar, bio, zona, origen, redes y media.
- [x] Anuncios con bloque publico y bloque HOT.
- [x] Galeria publica/privada por anuncio.
- [x] Content Hub con cuota global inicial de 35 MB.
- [x] Lanzadores concentrados en `launchers/`.
- [x] Documentacion inicial en `docs/`.
- [x] Contacto directo en anuncio: llamada, WhatsApp y Telegram.
- [x] Campos de contacto profesional editables desde perfil.
- [x] Dashboard profesional con checklist de activacion y progreso.
- [x] Django Admin registra usuarios, perfiles, media, anuncios, imagenes, servicios y transacciones.
- [x] Launcher principal optimizado: ya no borra cache Python en cada arranque.
- [x] Limpieza de cache protegida para no tocar `venv`, `.venv`, `.git`, `media`, `backups` ni `node_modules`.
- [x] Configuracion por entorno, zona horaria local y protecciones para produccion.
- [x] Suite automatizada inicial de 24 pruebas criticas.
- [x] Launcher `VERIFY_PROJECT.bat`.
- [x] Semillado de categorias convertido en management command.
- [x] Recarga online de Tangas con pasarela abstraida (BaseGateway + registry + dummy).
- [x] Webhook de pago con validacion de importe/moneda, acreditacion atomica e idempotente.
- [x] Gestion visual de paquetes de Tangas (crear, editar, desactivar, eliminar) en panel de control.
- [x] Paquetes de Tangas, ordenes de recarga y logs de webhook registrados en Django Admin.
- [x] Variable de entorno `AHHH_PAYMENT_MODE` (test/live) validada al arrancar.
- [x] Documento de pasarela: `docs/pagos_pasarela.md`.
- [x] Suite ampliada a 63 tests (flujo de recarga, idempotencia, control de paquetes).
- [x] Recuperacion de contrasena por email (flujo completo de Django, SMTP configurable por `.env`, rate-limited) con 6 tests.
- [x] Cambio de contrasena desde sesion iniciada (Django PasswordChangeView, rate-limited) con 6 tests.
- [x] `init_admin` asigna correo al superadmin desde `AHHH_ADMIN_EMAIL` (idempotente, sin tocar la contrasena) con 5 tests.
- [x] Exencion de cobro de Tangas por anuncio (solo superadmin): los anuncios exentos no pagan Tangas aunque tengan plan de pago (ni cobro diario ni primer dia) y no se les exige saldo; motivo opcional visible en el panel de control.

## Ahora - Fase 1: Estabilizacion Tecnica

- [x] Diagnosticar bloqueo de `manage.py check` / `django.setup()`.
- [x] Corregir referencias a `ad.image` en plantillas.
- [x] Conectar ruta de `delete_ad_image`.
- [x] Ajustar dashboard a estados reales: `ACTIVE` y `CERRADO`.
- [x] Corregir enlaces muertos de home y acciones principales.
- [x] Retirar logica temporal para usuarios concretos.
- [x] Revisar `maintenance/clean_structure.py` para evitar borrados peligrosos de migraciones.
- [x] Confirmar rutas publicas principales: home, login, registro y detalle de anuncio.
- [x] Confirmar render de dashboard autenticado.
- [x] Confirmar por pruebas el flujo autenticado: roles, crear anuncio, favoritos y borrado seguro.
- [x] Levantar servidor local y revisar visualmente home/detalle publico.
- [ ] Revisar visualmente dashboard autenticado.
- [x] Dashboard profesional con anuncios en tarjetas responsive para movil y PC.
- [x] Ocultar Tangas de todas las vistas publicas; solo aparecen en entorno profesional/admin.

## Siguiente - Fase 2: Producto Minimo Lanzable

- [x] Buscador sencillo por texto y zona.
- [x] Retirar selector de categoria de la portada.
- [x] Contacto real por llamada, WhatsApp y Telegram.
- [x] Cliente registrado puede acceder al contenido HOT.
- [x] Cliente registrado puede marcar/quitar favoritas desde home, detalle y panel cliente.
- [x] Panel cliente mobile-first con favoritas y perfiles activos.
- [x] Profesionales pueden ver los perfiles privados de clientes que las marcaron como favoritas.
- [ ] Revisar formato y obligatoriedad de datos de contacto profesional.
- [ ] Mejorar mensajes de cuota y subida de media.
- [ ] Mensajes de exito/error visibles.
- [x] Convertir tabla de anuncios del dashboard en tarjetas responsive.
- [x] Revision responsive de home y detalle a 360, 768 y 1280 px.
- [ ] Revision movil autenticada de dashboard y formularios.
- [ ] Textos legales y protocolo de seguridad revisados.
- [ ] Pruebas de humo documentadas.
- [x] Menu de navegacion compacto para telefono.
- [x] Barra fija de llamada, WhatsApp y Telegram en detalle movil.

## Fase 3: Cuotas, Pagos y Retencion

- [x] Compra online de Tangas con pasarela simulada (dummy) para desarrollo.
- [x] Estados de orden de recarga: PENDING, PAID, FAILED, CANCELLED, REFUNDED.
- [x] Acreditacion de saldo atomica e idempotente con `select_for_update`.
- [ ] Elegir pasarela real adulto-friendly y conectarla al contrato `BaseGateway`.
- [ ] Firmar y validar webhook real + URL HTTPS publica para notificaciones.
- [ ] Definir modelo de suscripcion profesional.
- [ ] Guardar ultima actividad real del profesional.
- [ ] Implementar estados de pago de profesional: activo, impagado, gracia, suspendido, eliminado.
- [ ] Politica de reembolso (el stub `refund_order` no descuenta Tangas ya gastadas).
- [ ] Crear comando de limpieza con modo simulacion.
- [ ] Crear launcher `.bat` para auditoria/limpieza segura.
- [ ] Documentar politica final de retencion.

## Fase 4: Admin / Patricia Control Panel

- [x] Admin basico potente para usuarios, perfiles, media, anuncios, servicios y transacciones.
- [x] Panel visual inicial para superadmin en `/accounts/control/`.
- [x] Vista visual de profesionales con tarjetas/lista.
- [x] Vista visual de clientes para superadmin con acceso a ficha de intervencion.
- [ ] Panel de profesionales por estado de pago y cuota usada.
- [ ] Acciones admin: suspender, reactivar, borrar media, ampliar cuota.
- [ ] Reportes basicos de altas, anuncios, uso de disco y pagos.

## Nota de Revision Actual

- [x] Superadmin redirige al panel visual; Django queda plegado como respaldo tecnico.
- [x] Pamela puede guardar cambios de perfil correctamente a nivel backend.
- [x] Redisenar pantalla de perfil profesional con experiencia guiada y menos formulario simple.
- [x] Redisenar pantalla de crear/editar anuncio con secciones visuales y acciones claras.
- [ ] Revisar manualmente en movil perfil profesional y formulario de anuncio.
- [x] Superadmin redirige a `/accounts/control/` y ve boton CONTROL en navegacion.
- [x] Superadmin tiene vista visual de profesionales con tarjetas/lista.
- [x] Documentar journeys UX de profesional, cliente y superadmin.
- [x] Ficha visual editable de usuario/profesional para superadmin.
- [x] Ficha visual editable de cliente para superadmin, incluyendo perfil privado, galeria y favoritas.
- [x] Edicion visual de anuncios desde superadmin.
- [x] Subida y borrado de fotos publicas/HOT de anuncios desde superadmin.
- [x] Galeria interna del profesional gestionable desde superadmin.
- [x] Crear anuncios para un profesional desde superadmin.
- [x] Usar fotos de galeria interna en anuncios desde superadmin.
- [x] Papelera de superadmin para perfiles, anuncios y material multimedia.
- [x] Seleccion multiple de profesionales para enviar a papelera.
- [x] Purga definitiva de elementos seleccionados o vaciado completo de papelera.
- [x] Productos de promocion configurables por Patricia.
- [x] Anuncios enlazados a producto de promocion elegido por profesional o superadmin.
- [x] Estrategia de visibilidad por prioridad del producto.
- [x] Recarga manual de Tangas por superadmin con transaccion registrada.
- [x] Launcher de pruebas por Tailscale/LAN: `launchers/RUN_TAILSCALE.bat`.
- [ ] Flujo profesional por pasos para movil.
- [x] Preview compacta del anuncio mientras se edita.
- [ ] Estados visuales claros durante subida de fotos/videos.
- [x] Crear/editar anuncio convertido en flujo guiado mobile-first.
- [ ] Acciones seguras desde ficha admin: suspender/reactivar, borrar material, ampliar cuota.
- [x] Edicion visual propia de anuncios desde superadmin sin pasar por Django Admin.
- [x] Listado global visual de anuncios con filtros y acceso a edicion.
- [x] Galeria global de materiales con moderacion y miniaturas.
- [x] Historial visual global de movimientos de Tangas.
- [x] Gestion visual de servicios asignables a anuncios.
- [x] Configuracion global editable sin Django Admin.
- [x] Auditoria completa de rutas administrativas sin fugas operativas a `/admin/`.
- [x] Auditoria completa de rutas cliente y profesional sin fugas a `/admin/`.
- [x] Cartera profesional visual para Tangas y solicitud de recarga.
- [x] Pago online de la recarga: orden PENDING, checkout, webhook y acreditacion.
- [x] Control visual de paquetes de Tangas (precio, cantidad, orden, activo).
- [x] Gestion de paquetes/ordenes/webhooks tambien desde Django Admin.
- [ ] Mostrar historial de ordenes de recarga en la cartera profesional.
- [x] Navegacion funcional entre informacion publica y contenido HOT.
- [x] Corregir desbordamiento de cabecera profesional con nombres largos.
- [ ] Historial/auditoria de acciones de moderacion.
- [ ] Extender el flujo profesional para elegir material desde su galeria interna al crear anuncios.
- [x] Restaurar elementos individualmente, por seleccion o en bloque desde papelera.
- [ ] Mostrar estimacion mas precisa de memoria por elemento en papelera.
- [ ] Consumo real de saldo Tangas al activar/renovar producto de promocion.
- [ ] Fecha de caducidad de promocion por duracion del producto.
- [ ] Auditoria ampliada de recargas manuales con motivo obligatorio y filtros.
