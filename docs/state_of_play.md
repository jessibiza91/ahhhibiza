# Estado Actual - Ahhh! Ibiza

Ultima revision: 2026-08-12.

Documentos de referencia:

- `docs/roadmap.md`: vision y fases maestras.
- `docs/consolidation_route_map_2026-07-05.md`: ejecucion activa.
- `docs/ux_product_audit_2026-06-20.md`: auditoria de producto y UX.
- `docs/cableado_flows_audit_2026-06-20.md`: auditoria funcional.
- `docs/pagos_pasarela.md`: pasarela de pago (arquitectura y pendientes).

## Estado General

La plataforma es un prototipo avanzado funcional en consolidacion. Los flujos principales de cliente, profesional y superadmin existen, y las rutas criticas tienen una primera suite automatizada (63 tests).

El ciclo de compra online de Tangas esta implementado con una pasarela simulada (`dummy`) que permite probar de punta a punta sin cobrar. No esta lista para cobrar de verdad: falta elegir una pasarela adulto-friendly, conectar su webhook con firma en HTTPS y cerrar pagos, retencion y auditoria de moderacion.

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
- Cartera de Tangas con saldo, movimientos, solicitud y compra online de recarga (pasarela dummy en desarrollo).

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
- Paquetes de Tangas iniciales con `python manage.py seed_tangas_packages` (idempotente: no duplica ni pisa ediciones de Patricia).
- `CLEAN_CACHE.bat` usa la limpieza con exclusiones seguras.
- `VERIFY_PROJECT.bat` ejecuta checks, migraciones y tests.
- Suite de 24 tests para filtros, roles, HOT, favoritos, papelera, restauracion y superadmin.
- Operacion administrativa completa sin saltos al Django Admin.
- Listados visuales globales de anuncios, materiales y movimientos.
- Gestion visual de servicios y configuracion global.
- Cartera profesional visual con saldo, promociones, movimientos y solicitud de recarga.
- Compra online de Tangas: orden PENDING, checkout, webhook y acreditacion atomica e idempotente.
- Control visual de paquetes de Tangas (crear, editar, desactivar) desde el panel.
- Paquetes, ordenes y logs de webhook tambien registrados en Django Admin.
- Pasarela aislada tras `BaseGateway` + registry; `dummy` bloqueada en produccion y
  pasarela `disabled` para produccion sin pasarela real (bloquea la recarga online).
- `AHHH_PAYMENT_MODE` (test/live) validado al arrancar.
- Rutas cliente y profesional auditadas sin fugas a Django.
- Navegacion compacta en telefono.
- Barra de contacto fija en detalle para telefono.

## Validacion

- `python manage.py check`: correcto.
- `python manage.py check --deploy` con variables de produccion: correcto.
- `python manage.py makemigrations --check --dry-run`: sin cambios.
- `python manage.py test`: 63 tests correctos (filtros, roles, HOT, favoritos, papelera, restauracion, superadmin, recarga online y control de paquetes).
- Revision responsive en navegador a 360, 768 y 1280 px: sin desbordamiento horizontal.
- Filtros combinados y resultado de portada comprobados en navegador.
- Dato temporal de revision visual eliminado al finalizar.

## Pendiente Prioritario

1. Elegir pasarela de pago real adulto-friendly y conectar su webhook con firma en HTTPS (ver `docs/pagos_pasarela.md`).
2. Dividir la ficha extensa de superadmin en secciones o pestanas.
3. Revisar visualmente formularios autenticados de perfil y anuncio en telefono real.
4. Incorporar estados de subida y mensajes de exito/error mas claros.
5. Registrar acciones de moderacion.
6. Definir consumo, caducidad y renovacion de promociones en Tangas.
7. Definir pago, gracia, suspension y retencion antes de automatizar borrados.
8. Preparar hosting, dominio, HTTPS, static/media y backups restaurables.

## Decisiones Pendientes

- Hosting y dominio final (condiciona el webhook HTTPS de la pasarela).
- Pasarela de pago real adulto-friendly y precio final de los paquetes de Tangas.
- Regla exacta de consumo y renovacion de Tangas.
- Politica de reembolso de recargas.
- Periodos de gracia y retencion por impago o inactividad.
- Cuota inicial de almacenamiento.
- Conservacion o retirada del entorno `.venv`; los launchers usan `venv`.
