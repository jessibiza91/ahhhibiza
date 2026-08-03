# Journeys UX - Profesional, Cliente y Superadmin

Este documento describe la experiencia ideal de uso simulando personas reales, especialmente en movil.

## Principio General

La web debe sentirse como una herramienta visual, no como un formulario administrativo. Django puede seguir siendo el motor tecnico, pero la experiencia diaria debe vivir en pantallas propias, con tarjetas, miniaturas, iconos claros y acciones tactiles.

## Profesional

Persona simulada: profesional adulta que quiere anunciarse desde un movil o tablet, sin conocimientos informaticos.

### Objetivo

Crear una presencia publica atractiva, subir material, separar contenido publico y privado, activar anuncios y renovar visibilidad con Tangas sin confundirse.

### Viaje Ideal

1. Registro como profesional.
2. Entrada directa a un panel con progreso: perfil, contacto, galeria, primer anuncio y promocion.
3. Edicion de perfil en bloques cortos:
   - foto principal;
   - descripcion;
   - zona;
   - contacto directo;
   - redes opcionales;
   - galeria profesional.
4. Subida de fotos/videos desde movil con miniaturas inmediatas.
5. Eliminacion de material con una X pequena sobre cada miniatura.
6. Creacion de anuncio en dos zonas:
   - publico: visible para cualquier visitante;
   - privado/HOT: solo usuarios registrados.
7. Vista previa real del anuncio antes o despues de guardar.
8. Recarga y consumo de Tangas solo dentro del entorno profesional.

### Dolor Actual Detectado

- Las pantallas ya son mas visuales, pero siguen siendo largas.
- Faltan microestados claros al subir archivos: subiendo, subido, error, cuota superada.
- En movil, cualquier accion oculta por hover puede fallar.
- Falta una vista previa compacta permanente de como queda el anuncio.
- Falta un flujo tipo asistente para alta inicial: paso actual, siguiente paso y completado.

### Criterios de Calidad

- Un boton principal por pantalla.
- Acciones secundarias visibles pero menos pesadas.
- Miniaturas siempre visibles y borrado siempre accesible en tactil.
- Lenguaje simple: "Fotos publicas", "Fotos privadas", "Guardar y ver".
- La profesional no debe preguntarse si algo es publico o privado.

## Cliente

Persona simulada: visitante desde movil que quiere descubrir perfiles, comparar rapido y contactar.

### Objetivo

Encontrar perfiles activos, entender que se puede ver publicamente, desbloquear contenido privado si se registra, crear una presentacion privada y contactar por llamada, WhatsApp o Telegram.

### Viaje Ideal

1. Entra y acepta age gate.
2. Ve tarjetas reales con foto, zona, resumen y señales de disponibilidad.
3. Filtra por zona, servicios y busqueda.
4. Abre un detalle con foto grande, descripcion publica y botones de contacto.
5. Ve claramente que contenido HOT requiere registro.
6. Si se registra, desbloquea descripcion privada, fotos privadas y redes.
7. Entra a su panel cliente con favoritas y perfiles activos.
8. Completa un perfil privado con datos reales o discretos, avatar y fotos opcionales.
9. Marca como favoritas las profesionales que quiere seguir revisando.
10. Esas profesionales pueden ver su perfil privado para generar confianza.
11. Contacta con botones grandes y tactiles.

### Dolor Actual Detectado

- Falta buscador/filtros reales.
- El detalle no tiene aun una barra sticky de contacto en movil.
- El contenido privado se desbloquea para clientes registrados y ya existe panel de favoritas.
- El cliente ya puede crear perfil privado con galeria; solo lo ven profesionales favoritas y superadmin.
- Puede hacerse mas clara la separacion visual entre publico, HOT y contacto en movil.

## Superadmin

Persona simulada: administradora no tecnica que necesita controlar usuarios, pagos, materiales y anuncios.

### Objetivo

Gestionar la plataforma sin entrar al Django Admin salvo para casos tecnicos.

Patricia no es cliente ni profesional. Es la gestora del sistema y dispone de un modo de intervencion directa sobre perfiles, galerias y anuncios. Este modo es intencionadamente invasivo: existe para ayudar a usuarios que no saben gestionar su perfil y para moderar material ilegal, inadecuado o contrario a la politica de la plataforma.

### Viaje Ideal

1. Login como Patricia.
2. Entrada directa al panel visual.
3. Metricas principales: profesionales, clientes, anuncios, materiales, incidencias.
4. Listado de profesionales en tarjetas/lista.
5. Ficha de cada profesional:
   - estado de cuenta;
   - saldo Tangas;
   - anuncios;
   - materiales publicos y privados;
   - uso de espacio;
   - acciones: editar, suspender, reactivar, borrar material, ampliar cuota.
6. Intervencion directa:
   - completar perfil;
   - subir/borrar material de galeria interna;
   - crear, editar, pausar o borrar anuncios;
   - incorporar material de galeria interna a anuncios como publico o HOT.
7. Auditoria de inactivos/impagados con modo simulacion antes de borrar.
8. Papelera:
   - revisar perfiles, anuncios y material retirado;
   - seleccionar elementos concretos;
   - vaciar toda la papelera;
   - entender que la papelera sigue ocupando memoria hasta purga definitiva.
9. Productos de promocion:
   - crear categorias internas de anuncio;
   - asignar precio en Tangas;
   - definir visibilidad y prioridad;
   - activar/desactivar productos elegibles por profesionales.
10. Recargas manuales:
   - ajustar saldo de Tangas de un profesional;
   - introducir concepto;
   - dejar movimiento registrado en transacciones.
11. Clientes:
   - listar clientes en tarjetas;
   - abrir su ficha privada;
   - editar cuenta, perfil y galeria;
   - revisar profesionales favoritas;
   - retirar contenido inadecuado.

### Dolor Actual Detectado

- El panel visual ya empieza a sustituir al admin tecnico.
- Aun faltan fichas profundas propias para usuario/anuncio/material.
- Aun faltan acciones operativas seguras fuera del Django Admin.
- Patricia debe poder auditar y gestionar la galeria interna de cada profesional, porque es el banco de material desde el que se completan perfil y anuncios.
- La interfaz debe indicar claramente cuando Patricia esta en modo intervencion para evitar confundir esa operacion con una sesion normal de usuario.
- Borrar desde el panel de Patricia debe enviar a papelera. La eliminacion irreversible solo ocurre desde la papelera y con confirmacion.

## Prioridad de Implementacion

1. Profesional movil: subida/gestion de media, pasos claros y preview.
2. Cliente movil: buscador/filtros, favoritas y contacto sticky.
3. Superadmin: ficha visual de profesional y acciones seguras.
4. Tangas/renovacion: saldo, consumo, historial y estados de pago.
5. Limpieza segura: auditoria, gracia, suspension y borrado con `--dry-run`.
