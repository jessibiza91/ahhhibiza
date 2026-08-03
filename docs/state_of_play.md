# Estado Actual - Ahhh! Ibiza

Ultima revision: 2026-07-05.

Documentos de referencia:

- `docs/roadmap.md`: vision y fases maestras.
- `docs/consolidation_route_map_2026-07-05.md`: ejecucion activa.
- `docs/ux_product_audit_2026-06-20.md`: auditoria de producto y UX.
- `docs/cableado_flows_audit_2026-06-20.md`: auditoria funcional.

## Estado General

La plataforma es un prototipo avanzado funcional en consolidacion. Los flujos principales de cliente, profesional y superadmin existen, y las rutas criticas tienen una primera suite automatizada.

No esta lista para produccion comercial: faltan cerrar el ciclo real de Tangas, pagos, retencion, auditoria de moderacion y despliegue.

## Funcionalidad Estable

### Cliente y visitante

- Home con anuncios activos ordenados por prioridad.
- Busqueda combinable por texto publico y zona.
- Registro, login y panel privado de cliente.
- Acceso HOT para usuarios registrados.
- Favoritas desde home, detalle y panel.
- Perfil y galeria privados, visibles solo para profesionales favoritas y superadmin.
- Contacto por llamada, WhatsApp y Telegram.

### Profesional

- Perfil editable y galeria interna.
- Creacion y edicion guiada de anuncios.
- Galerias publica y HOT.
- Eleccion de producto de promocion.
- Dashboard visual responsive.
- Vista privada de clientes que marcaron sus anuncios como favoritos.

### Superadmin

- Patricia entra en el panel visual `/accounts/control/`.
- Gestion visual de profesionales y clientes.
- Intervencion directa sobre cuenta, perfil, contacto, galeria y anuncios.
- Creacion de anuncios y gestion multimedia por cuenta ajena.
- Productos de promocion y recarga manual de Tangas.
- Papelera central, seleccion multiple y purga definitiva.
- Restauracion individual, multiple o completa desde papelera.
- Los anuncios restaurados permanecen cerrados hasta revision para evitar una republicacion accidental.
- Django Admin permanece como respaldo tecnico, no como experiencia principal.

## Consolidacion Aplicada

- Copia SQLite previa en `backups/`.
- Settings configurables mediante variables `AHHH_*`.
- Zona horaria `Europe/Madrid`.
- Hosts de desarrollo explicitos y protecciones HTTPS para `DEBUG=False`.
- `.env.example` y `.gitignore`.
- `seed_tags.py` sustituido por `python manage.py seed_service_tags`.
- `CLEAN_CACHE.bat` usa la limpieza con exclusiones seguras.
- `VERIFY_PROJECT.bat` ejecuta checks, migraciones y tests.
- Suite de 24 tests para filtros, roles, HOT, favoritos, papelera, restauracion y superadmin.
- Operacion administrativa completa sin saltos al Django Admin.
- Listados visuales globales de anuncios, materiales y movimientos.
- Gestion visual de servicios y configuracion global.
- Cartera profesional visual con saldo, promociones, movimientos y solicitud de recarga.
- Rutas cliente y profesional auditadas sin fugas a Django.
- Navegacion compacta en telefono.
- Barra de contacto fija en detalle para telefono.

## Validacion

- `python manage.py check`: correcto.
- `python manage.py check --deploy` con variables de produccion: correcto.
- `python manage.py makemigrations --check --dry-run`: sin cambios.
- `python manage.py test`: 9 tests correctos.
- Revision responsive en navegador a 360, 768 y 1280 px: sin desbordamiento horizontal.
- Filtros combinados y resultado de portada comprobados en navegador.
- Dato temporal de revision visual eliminado al finalizar.

## Pendiente Prioritario

1. Dividir la ficha extensa de superadmin en secciones o pestanas.
2. Revisar visualmente formularios autenticados de perfil y anuncio en telefono real.
3. Incorporar estados de subida y mensajes de exito/error mas claros.
4. Registrar acciones de moderacion.
5. Definir consumo, caducidad y renovacion de promociones en Tangas.
6. Definir pago, gracia, suspension y retencion antes de automatizar borrados.
7. Preparar hosting, dominio, HTTPS, static/media y backups restaurables.

## Decisiones Pendientes

- Hosting y dominio final.
- Regla exacta de consumo y renovacion de Tangas.
- Periodos de gracia y retencion por impago o inactividad.
- Cuota inicial de almacenamiento.
- Conservacion o retirada del entorno `.venv`; los launchers usan `venv`.
