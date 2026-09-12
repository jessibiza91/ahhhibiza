# Routemap de Consolidacion - 2026-07-05

Este documento convierte las auditorias de producto, UX y cableado en una secuencia verificable. Su objetivo es estabilizar lo construido antes de ampliar pagos, retencion o despliegue.

## Criterio de Estabilidad

Una fase se considera estable cuando:

- el comportamiento tiene una prueba automatizada o una comprobacion reproducible;
- los permisos responden al rol correcto;
- las acciones destructivas usan POST y papelera cuando corresponde;
- la experiencia principal funciona en movil, tablet y escritorio;
- la documentacion refleja el estado real;
- no se mezclan secretos, datos locales o utilidades sueltas en la raiz.

## Fase 0 - Linea Base

Estado: completada.

- Auditoria de producto y UX realizada.
- Auditoria de rutas, permisos y flujos realizada.
- Copia de seguridad SQLite previa a consolidacion creada en `backups/`.
- Cero migraciones pendientes al inicio de la fase.

## Fase 1 - Seguridad y Orden Operativo

Estado: completada con una decision no destructiva pendiente.

- Configuracion sensible mediante variables de entorno.
- Zona horaria local `Europe/Madrid`.
- Hosts de desarrollo explicitos y configurables.
- Cookies y redireccion HTTPS reforzadas al usar `DEBUG=False`.
- Limpieza de cache delegada a la rutina con exclusiones seguras.
- Semillado de categorias convertido en comando Django.
- `.gitignore` y `.env.example` incorporados.
- Pendiente: decidir cual de los dos entornos virtuales conservar tras verificar dependencias.

## Fase 2 - Descubrimiento Cliente

Estado: completada.

- Busqueda de portada por texto publico.
- Filtro por zona.
- Selector de categoria retirado para mantener la busqueda inicial sencilla.
- Combinacion de filtros mediante URL compartible.
- Prioridad de promociones conservada dentro de los resultados.
- Estado vacio y limpieza de filtros.
- Validacion en navegador realizada a 360, 768 y 1280 px sin desbordamiento.

## Fase 3 - Pruebas Permanentes

Estado: completada en su primera cobertura critica.

- Home y filtros.
- Permisos cliente/profesional/superadmin.
- Visibilidad publica y HOT.
- Favoritos.
- Borrado seguro y papelera.
- Intervencion visual superadmin.

Resultado: 24 pruebas correctas mediante `python manage.py test`. El launcher
`launchers/VERIFY_PROJECT.bat` agrupa check, migraciones y suite.

## Fase 4 - Afinado Mobile-First

Estado: en ejecucion.

- Completado: navegacion compacta que no desborda.
- Completado: contacto fijo inferior en detalle de anuncio.
- Completado: todas las rutas operativas de Patricia usan pantallas propias.
- Completado: anuncios, materiales, movimientos, servicios y configuracion global tienen vistas visuales.
- Completado: recorridos cliente y profesional auditados hasta su ultimo nivel.
- Completado: cartera profesional propia y navegacion funcional del detalle.
- Ficha superadmin dividida en secciones o pestanas.
- Formularios largos revisados a 360, 768 y 1280 px.
- Sustitucion progresiva de `confirm()` por dialogos visuales.

## Fase 5 - Operacion y Ciclo Economico

Estado: pendiente de reglas definitivas.

- Consumo y caducidad real de promociones en Tangas.
- Historial de movimientos y renovaciones.
- Estado de pago profesional y periodo de gracia.
- Comando de retencion con `--dry-run`, notificacion y log.
- Completado: restauracion individual, multiple y total desde papelera.
- Los anuncios restaurados quedan cerrados hasta revision.
- Registro de acciones de moderacion.

Esta fase no debe borrar cuentas ni consumir saldo hasta fijar y probar las reglas de negocio.

## Fase 6 - Preparacion de Lanzamiento

Estado: pendiente.

- Base de datos y almacenamiento aptos para el hosting elegido.
- Static/media servidos fuera del servidor de desarrollo.
- HTTPS, dominio y correo transaccional.
- Backups restaurables.
- Revision legal y protocolo de contenido ilegal.
- Pruebas de humo en el entorno final.

## Orden de Ejecucion Actual

1. Cerrar Fases 1 y 2.
2. Crear y ejecutar la suite de Fase 3.
3. Aplicar y verificar Fase 4.
4. Diseñar las reglas exactas de Fase 5 antes de automatizar cobros o eliminaciones.
5. Ejecutar Fase 6 sobre el hosting decidido.
