# Route Map UX y Lanzamiento - Ahhh! Ibiza

Este documento traduce la vision del producto en mejoras concretas de experiencia para clientes, profesionales y administracion.

Journeys detallados: `docs/ux_user_journeys.md`.

## Norte de Experiencia

La plataforma debe sentirse clara, segura y premium:

- La experiencia se disena primero para movil: visita, contacto, dashboard profesional, subida de media y pagos.
- El profesional siempre sabe que le falta para estar visible y vender mejor.
- El cliente encuentra perfiles rapidamente, entiende que contenido ve y contacta sin friccion.
- La administracion ve quien paga, quien ocupa espacio y que cuentas deben revisarse.

## Regla Mobile-First

La mayoria del trafico esperado sera movil. Cada mejora debe validarse en una pantalla pequena antes de considerarse lista.

- Botones tactiles con area suficiente.
- Formularios en una columna clara.
- Acciones principales visibles sin buscar.
- Contacto rapido desde detalle de anuncio.
- Dashboard profesional usable con pulgar: progreso, cuota, media, anuncios y pagos.
- Priorizar tarjetas y bloques escaneables tambien en PC; usar tablas solo cuando aporten control masivo al superadmin.

## Pilar 1 - Profesional

Objetivo: que crear y mantener un perfil sea sencillo.

### Flujo ideal

1. Registro profesional.
2. Dashboard con checklist de activacion.
3. Completar identidad: avatar, descripcion, zona, edad/origen.
4. Completar contacto: telefono, WhatsApp o Telegram.
5. Subir media profesional.
6. Crear anuncio con parte publica y parte HOT.
7. Ver preview real.
8. Activar o renovar con Tangas.

### Criterios de calidad

- Ninguna pantalla debe dejar al profesional preguntandose "y ahora que".
- Subir fotos/videos debe dar feedback claro de cuota y errores.
- Crear anuncio debe ser paso a paso, con preview y estado.
- El dashboard debe mostrar progreso, saldo, cuota, anuncios y acciones principales.

## Pilar 2 - Cliente

Objetivo: descubrir, comparar y contactar rapido.

### Flujo ideal

1. Entra, acepta age gate.
2. Ve perfiles activos y destacados.
3. Filtra por zona, servicios y busqueda.
4. Abre detalle.
5. Ve contenido publico.
6. Se registra si quiere desbloquear zona HOT.
7. Completa un perfil cliente privado con datos opcionales y fotografias.
8. Guarda perfiles favoritos para volver rapido y permitir que esas profesionales vean su perfil privado.
9. Contacta por llamada, WhatsApp o Telegram.

### Criterios de calidad

- Home con resultados reales, no solo hero.
- Fichas con portada, zona, servicios y llamada clara.
- Detalle con contacto siempre visible en movil.
- Estados bloqueados claros, sin confundir.

## Pilar 3 - Tangas, Renovacion y Retencion

Objetivo: que el sistema de pago y espacio sea comprensible y administrable.

Los Tangas son moneda interna del profesional. No son un precio publico del servicio, no se muestran a clientes y solo sirven para recargar saldo, renovar anuncios y consumir promocion/prioridad.

### Flujo ideal

1. Profesional ve saldo y proxima renovacion.
2. Puede recargar Tangas.
3. Renovacion consume saldo o marca impago.
4. Si no paga, entra en gracia.
5. Si sigue sin pagar, se suspende visibilidad.
6. Tras retencion, se limpia media/cuenta segun politica.

### Criterios de calidad

- No borrar nada sin periodo de aviso y modo auditoria.
- Toda limpieza masiva debe tener `--dry-run`.
- Dashboard debe explicar cuanto queda de cuota y tiempo.

## Pilar 4 - Administracion

Objetivo: controlar plataforma sin tocar codigo.

Django Admin queda como respaldo tecnico. La operacion diaria debe hacerse desde un panel visual propio, con tarjetas, metricas y acciones claras.

- Ver profesionales por estado de pago.
- Ver uso de disco por profesional.
- Suspender/reactivar perfiles.
- Ejecutar auditorias de limpieza.
- Revisar anuncios y contenido.
- Modificar o borrar usuarios, perfiles, anuncios y materiales cuando sea necesario.
- Ver materiales publicos y HOT asociados a cada profesional.
- Auditar transacciones y saldo de Tangas.

## Sprints Propuestos

### Sprint 1 - Activacion Profesional

- [x] Contacto directo en anuncio: llamada, WhatsApp y Telegram.
- [x] Dashboard con checklist de perfil.
- [x] Indicador de perfil incompleto.
- [x] CTA principal segun estado: editar perfil, subir media, crear anuncio.
- [ ] Mensajes de cuota claros.
- [x] Convertir anuncios del dashboard en tarjetas responsive para movil y PC.
- [ ] Convertir el alta profesional inicial en flujo guiado por pasos.
- [x] Preview compacta del anuncio durante edicion.
- [ ] Estados visuales completos de subida: subiendo, subido, error y cuota superada.

### Sprint 2 - Descubrimiento Cliente

- [ ] Buscador real en home.
- [ ] Filtros por zona y servicios.
- [ ] Tarjetas con portada real y link al detalle.
- [x] Panel cliente registrado con favoritas y perfiles activos.
- [x] Guardar/quitar favoritas desde home, detalle y panel.
- [x] Contenido HOT visible para clientes registrados.
- [x] Perfil privado de cliente con galeria.
- [x] Profesionales ven perfiles privados de clientes que las marcaron como favoritas.
- [ ] Contacto sticky en detalle movil.
- [ ] Diferenciar mejor en movil contenido publico y contenido HOT bloqueado.

### Sprint 3 - Publicacion Guiada

- [x] Formulario de anuncio por bloques mas claro.
- [ ] Validar minimo de descripcion publica.
- [ ] Recomendar al menos una imagen publica.
- [x] Preview antes de publicar.

### Sprint 4 - Tangas y Renovacion

- [ ] Modelo de suscripcion profesional.
- [ ] Fecha `paid_until`.
- [ ] Estado de pago.
- [ ] Recarga/consumo de Tangas.
- [ ] Avisos de impago/gracia.

### Sprint 5 - Limpieza Segura

- [ ] Comando `cleanup_professionals --dry-run`.
- [ ] Launcher de auditoria.
- [ ] Log de candidatos a limpieza.
- [ ] Politica final de retencion.

### Sprint 6 - Superadmin Operativo

- [x] Registrar usuarios, perfiles, media, anuncios, imagenes, servicios y transacciones en Django Admin.
- [x] Filtros, busquedas y acciones basicas para usuarios y anuncios.
- [x] Borrado fisico de archivos al eliminar media desde admin.
- [x] Dashboard propio de superadmin con metricas agregadas.
- [x] Vista visual de profesionales con tarjetas/lista, miniaturas y accesos rapidos.
- [x] Vista visual de clientes con tarjetas y acceso a ficha de intervencion.
- [x] Ficha visual editable de usuario/profesional sin entrar en Django Admin.
- [x] Edicion visual de anuncios desde superadmin con textos, estado, Tangas, servicios y media publica/HOT.
- [x] Gestion visual de galeria interna del profesional desde su ficha de superadmin.
- [x] Crear anuncios para un profesional desde superadmin.
- [x] Incorporar fotos de la galeria interna a anuncios como publicas o HOT desde superadmin.
- [x] Papelera de reciclaje con perfiles, anuncios y material multimedia.
- [x] Eliminacion definitiva de seleccionados o vaciado completo de papelera.
- [x] Productos de promocion con precio en Tangas y prioridad de visibilidad.
- [x] Profesionales eligen producto de promocion al crear/editar anuncio.
- [x] Recarga manual de Tangas desde ficha de superadmin.
- [ ] Acciones de suspender/reactivar profesional.
- [ ] Vista de uso de almacenamiento por profesional.
- [ ] Auditoria de materiales por usuario.
- [ ] Ficha visual propia de profesional con materiales publicos/privados y acciones seguras.

## Primer Cambio en Marcha

Siguiente mejora recomendada: mejorar la gestion de cuota/media con mensajes claros antes, durante y despues de subir archivos.

Actualizacion: superadmin ya tiene panel visual propio en `/accounts/control/`; Django Admin queda como respaldo tecnico.
- Actualizacion: perfil profesional y crear/editar anuncio tienen primer rediseño visual guiado.
- Actualizacion: gestion de profesionales ya cuenta con pantalla propia en `/accounts/control/profesionales/`, con modo tarjeta/lista.
- Actualizacion tecnica: el launcher principal ya no limpia `.pyc` en cada arranque para evitar inicios lentos.
- Actualizacion: crear/editar anuncio ya funciona como flujo guiado en 4 pasos, con preview compacta y barra de acciones movil.
- Actualizacion: Patricia ya puede abrir una ficha visual de usuario en `/accounts/control/usuario/<id>/` y editar cuenta, perfil, contacto, Tangas, avatar, redes y estado sin pasar por Django Admin.
- Actualizacion: Patricia ya puede editar anuncios desde `/control/anuncio/<id>/`, subir/borrar fotos publicas y HOT, pausar anuncios y corregir contenido sin entrar en Django Admin.
- Actualizacion: la ficha de usuario incluye galeria interna completa con subida y borrado de material; la pantalla de anuncio permite usar fotos de esa galeria como material publico o HOT.
- Actualizacion: papelera disponible en `/accounts/control/papelera/`; enviar a papelera conserva datos/archivos y la purga definitiva libera memoria.
- Actualizacion: Patricia gestiona productos de promocion en `/control/promociones/`; la visibilidad publica usa el peso de prioridad del producto.
- Actualizacion: Patricia puede recargar Tangas manualmente desde la ficha del profesional y queda registro en transacciones.
- Actualizacion: el cliente registrado ya tiene panel propio en `/accounts/cliente/`, favoritos y acceso visual al contenido HOT desbloqueado.
- Actualizacion: el cliente puede crear perfil privado con fotos; solo lo ven profesionales favoritas y Patricia. Las profesionales tienen vista propia de esos clientes.

## Nota de Revision Actual

- Superadmin: redireccion y boton ADMIN implementados.
- Perfil profesional: funcional, pero pendiente de rediseño guiado.
