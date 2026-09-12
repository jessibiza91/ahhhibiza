# Auditoria de Rutas Cliente y Profesional - 2026-07-05

Objetivo: asegurar que clientes y profesionales usan interfaces propias,
intuitivas y mobile-first hasta el ultimo nivel de cada recorrido.

## Cliente

| Accion | Ruta visual |
| --- | --- |
| Panel privado | `/accounts/cliente/` |
| Editar perfil y galeria privada | `/accounts/perfil/editar/` |
| Buscar profesionales | `/` |
| Ver anuncio y contenido HOT | `/<id>/` |
| Guardar o retirar favorita | `/accounts/favoritos/<id>/toggle/` |

Validado:

- Ninguna pantalla contiene enlaces a `/admin/`.
- El contenido HOT se desbloquea al iniciar sesion.
- El perfil privado no tiene ruta publica.
- Un cliente no puede crear anuncios ni abrir la cartera profesional.
- Dashboard, perfil y detalle no desbordan a 360 px.

## Profesional

| Accion | Ruta visual |
| --- | --- |
| Dashboard | `/accounts/dashboard/` |
| Perfil y galeria | `/accounts/perfil/editar/` |
| Cartera y movimientos | `/accounts/dashboard/tangas/` |
| Crear anuncio | `/crear/` |
| Editar anuncio | `/anuncio/editar/<id>/` |
| Ver anuncio | `/<id>/` |
| Ver clientes favoritas | `/accounts/dashboard/clientes-favoritos/` |

Validado:

- Ninguna pantalla contiene enlaces a `/admin/`.
- La edicion solo permite anuncios del propietario.
- Los borrados usan POST y papelera.
- La cartera muestra saldo, promociones y movimientos internos.
- La solicitud de recarga tiene un destino real de soporte.
- Un profesional no puede entrar al panel privado de cliente.
- Las seis capas operativas no desbordan a 360 px.

## Correcciones Aplicadas

- El boton muerto `RECARGAR TANGAS` abre ahora una cartera profesional propia.
- La cartera permite solicitar recarga sin simular una pasarela aun inexistente.
- Las pestanas del detalle navegan a informacion publica y zona HOT.
- La redireccion posterior a favoritos solo admite destinos internos seguros.
- La cabecera del dashboard profesional se adapta a nombres largos en telefono.
- El contenedor global usa el ancho util real y evita desplazamientos laterales.

## Resultado

- Cero enlaces Django en rutas cliente/profesional.
- Cero enlaces vacios o acciones `#` sin destino.
- 24 pruebas automatizadas correctas.
- Recorrido autenticado real a 360 px con cuentas temporales.
- Cuentas y anuncio temporales eliminados al terminar.
