# Auditoria de Rutas Administrativas - 2026-07-05

Objetivo: impedir que el trabajo cotidiano de Patricia termine en el Django
Admin y asegurar una interfaz visual propia hasta el ultimo nivel operativo.

## Resultado

Todas las rutas de trabajo habituales tienen pantalla propia:

| Area | Ruta visual |
| --- | --- |
| Panel principal | `/accounts/control/` |
| Profesionales | `/accounts/control/profesionales/` |
| Clientes | `/accounts/control/clientes/` |
| Ficha completa de usuario | `/accounts/control/usuario/<id>/` |
| Anuncios globales | `/control/anuncios/` |
| Edicion completa de anuncio | `/control/anuncio/<id>/` |
| Creacion por cuenta del profesional | `/control/usuario/<id>/anuncio/crear/` |
| Materiales globales | `/accounts/control/materiales/` |
| Movimientos de Tangas | `/accounts/control/movimientos/` |
| Productos de promocion | `/control/promociones/` |
| Servicios asignables | `/control/servicios/` |
| Configuracion global | `/accounts/control/configuracion/` |
| Papelera y restauracion | `/accounts/control/papelera/` |

## Correcciones de Cableado

- Los anuncios recientes abren el editor visual propio.
- Los movimientos recientes llevan a la ficha financiera del usuario.
- Los botones de anuncios por profesional abren el listado visual filtrado.
- Los botones de galeria abren la ficha visual en su seccion de materiales.
- La galeria global permite retirar media a papelera sin mostrar JSON ni Django.
- Se retiraron botones Django de fichas de usuario, anuncios, clientes y profesionales.
- Se retiro Django de la navegacion superior.

## Excepcion Tecnica

`/admin/` se conserva para diagnostico o recuperacion excepcional. Existe un solo
enlace, dentro de `Herramientas tecnicas de emergencia`, plegado al final del
panel principal. No forma parte de ningun recorrido operativo.

## Validacion

- Busqueda de plantillas: una sola referencia `admin:`, la excepcion tecnica.
- Suite global de 24 pruebas automatizadas correctas.
- Recorrido autenticado real con Patricia.
- Nueve pantallas administrativas verificadas a 360 px.
- Cero enlaces `/admin/` en las pantallas operativas.
- Cero desbordamientos horizontales detectados.
