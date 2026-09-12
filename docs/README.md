# Documentacion - Ahhh! Ibiza

Indice maestro de la documentacion. La idea es simple: **segun lo que necesites,
lees un solo documento**. No hace falta leer mas.

## Que leer segun tu caso

| Necesitas...                          | Lee                                                       |
| ------------------------------------- | --------------------------------------------------------- |
| Desplegar o redesplegar en produccion | `docs/despliegue.md` (unica guia operativa, de 0 a prod)  |
| Entender en que estado esta el proyecto | `docs/state_of_play.md`                                |
| Conocer la vision y las fases         | `docs/roadmap.md`                                          |
| Ver que tareas hay pendientes         | `docs/todo.md`                                             |
| Integrar la pasarela de pago          | `docs/pagos_pasarela.md`                                   |
| Reglas al contribuir al codigo        | `docs/handover_report.md`                                  |
| Estandares de UI/UX                   | `docs/blueprint.md`                                        |
| Experiencia ideal por rol (UX)        | `docs/ux_user_journeys.md`                                 |
| Notas de trabajo historicas           | `docs/archivo/` (solo consulta, no son fuente de verdad)   |

## Orden de lectura sugerida

Si empiezas de cero en el proyecto, el minimo para orientarte es:

1. `README.md` (raiz) - que es esto y como se ejecuta en local.
2. `docs/state_of_play.md` - estado actual, incluida la produccion real.
3. `docs/roadmap.md` - hacia donde va.

Para **desplegar**, solo necesitas `docs/despliegue.md` (el README de la raiz te
lleva alli). El resto de documentacion no es necesaria para esa tarea.

## Regla

- `docs/state_of_play.md`, `docs/roadmap.md` y `docs/todo.md` son las unicas
  "fuentes de verdad vivas" de estado, vision y tareas.
- `docs/archivo/` contiene notas de trabajo (auditorias y route maps) que se
  conservan por contexto historico, pero **no se usan para conocer el estado**.