---
name: sdd-spec-writer
description: Genera specs/00X-<nombre>/spec.md para un módulo o funcionalidad nueva de un proyecto que sigue la metodología SDD (Spec-Driven Development). Lee docs/constitution.md y, si existe, docs/arquitectura.md u otro documento de referencia del proyecto, para sacar el contexto ya decidido, detecta el siguiente número de carpeta libre en specs/, hace preguntas de aclaración una por una (máx. 6) y produce la especificación completa con requisitos funcionales en notación EARS. Usa esta skill SIEMPRE que el usuario pida crear, especificar, definir los requisitos de, o redactar el spec de un módulo/funcionalidad nueva — aunque no diga explícitamente "SDD", "spec.md" o "EARS". Por ejemplo: "vamos a especificar el módulo de cobro", "necesito definir los requisitos de reportes", "crea la spec de mesas y pedidos", "especifiquemos la siguiente funcionalidad". NO uses esta skill para escribir plan.md, tasks.md, ni para implementar código — solo para la fase de especificación.
---

# SDD Spec Writer

Esta skill produce la especificación (`spec.md`) de una funcionalidad dentro de un proyecto que sigue Spec-Driven Development. Una spec buena es la que evita que el código se construya sobre ambigüedades — por eso el valor real de esta skill no es solo generar el archivo con la estructura correcta, sino **detectar y cerrar las ambigüedades antes de escribir nada**, apoyándote en preguntas dirigidas al usuario y en un chequeo final de puntos ciegos comunes.

No escribas código en ningún momento. Esta skill solo produce el QUÉ y el POR QUÉ de una funcionalidad — nada de stack, arquitectura, nombres de archivo o endpoints (eso pertenece a `plan.md`, fuera del alcance de esta skill).

## Paso 1: reunir el contexto

Antes de preguntar nada al usuario, reúne todo el contexto que ya existe para no hacer preguntas que ya tienen respuesta en el proyecto:

1. Lee `docs/constitution.md` — como mínimo, contiene las reglas innegociables del proyecto (stack, principios de simplicidad, trazabilidad, permisos, tests), que todo lo que generes debe respetar.
2. Busca también `docs/arquitectura.md` (o cualquier otro documento de referencia del proyecto, ej. `docs/contexto.md`, `docs/requisitos-generales.md`). Si existe, es la fuente principal de las decisiones de negocio y producto ya tomadas (roles, entidades, flujos, reglas). Si NO existe un documento separado, no lo eches en falta: trata `docs/constitution.md` como la única fuente disponible y revisa si además de los principios contiene decisiones de negocio ya definidas — muchos proyectos concentran todo ahí.
3. Extrae de cualquiera de esos documentos lo específicamente relacionado con el módulo que el usuario quiere especificar; no le pidas al usuario que te repita algo que ya está documentado, sea cual sea el archivo donde viva.
4. Revisa la carpeta `specs/` existente: mira qué módulos ya se especificaron (para no repetir requisitos que ya viven en otra spec) y detecta el siguiente número de carpeta libre (si el último es `003-...`, el nuevo módulo es `004-<nombre-en-kebab-case>`).

Si ningún documento del proyecto cubre el módulo pedido, dile al usuario qué información específica falta y pídesela directamente — no inventes decisiones de negocio que no estén documentadas ni confirmadas por el usuario.

## Paso 2: hacer preguntas, una por una

Con el contexto ya reunido, identifica qué queda ambiguo específicamente para este módulo (casos límite, comportamiento ante errores, qué queda fuera del MVP, quién puede hacer qué). Pregunta **una pregunta a la vez** — nunca una lista completa de golpe — y espera la respuesta antes de la siguiente. Máximo 6 preguntas.

Antes de preguntar cualquier cosa que ya esté decidida en `docs/arquitectura.md` o `docs/constitution.md`, verifica que de verdad no esté ahí — repetir una pregunta ya respondida en otro documento hace perder confianza en la skill.

### Puntos ciegos comunes a revisar siempre

Estos son los tipos de ambigüedad que más veces se cuelan en una spec y solo se detectan después, ya en la fase de clarificación — mejor prevenirlos aquí. Revisa si aplican al módulo que estás especificando, y si es así, conviértelos en preguntas:

- **Alcance de unicidad**: si algo debe ser "único" (un nombre, un código), ¿único dentro de qué conjunto? (ej. ¿único por rol, o único en todo el sistema?)
- **Reglas de formato**: cualquier campo que el usuario escribe (nombres, claves, códigos) necesita longitud, caracteres permitidos, y si distingue mayúsculas/minúsculas — no basta con "debe ser único", hay que decir cómo se compara.
- **Estados automáticos vs. decisiones humanas**: no mezcles un estado que cambia por una decisión de negocio (ej. "desactivar porque ya no trabaja aquí") con uno que cambia automáticamente por el sistema (ej. "bloqueado por seguridad") — si se comparten el mismo campo, alguien pierde información útil. Pregunta si deben ser estados independientes.
- **Quién puede hacer cada acción**: no des por hecho que "el admin" es el único rol relevante — pregunta explícitamente si cada acción sensible (crear, editar, eliminar, aprobar, cobrar, cancelar) la puede hacer también otro rol, y si hay alguna acción que un rol NO debería poder hacer sobre su propio registro o el de otro con el mismo rol.
- **Qué pasa con sesiones/accesos activos** cuando cambia el estado de una cuenta (se bloquea, se desactiva, se le cambia la clave) — ¿se cierran de inmediato o siguen activos hasta que expiren solos?
- **Entidades dependientes**: si A depende de B (ej. productos dentro de una categoría, pedidos en una mesa), ¿qué pasa con A cuando B se desactiva o elimina? Nunca lo dejes implícito.
- **Concurrencia simple**: ¿qué pasa si dos personas intentan la misma acción sensible casi al mismo tiempo (dos admins editando lo mismo, dos meseros tomando la misma mesa)? No hace falta una solución sofisticada, pero sí una regla explícita.
- **Complejidad de credenciales/seguridad**: si el módulo crea o cambia contraseñas, PIN o claves de acceso, define la regla de validación explícitamente (longitud mínima, combinación de caracteres) — "debe ser segura" no es un requisito verificable.
- **Módulos de solo lectura/reportes**: si el módulo consulta o resume datos en vez de crearlos, pregunta explícitamente qué se incluye o excluye del cálculo (ej. ¿los ítems anulados cuentan en el total? ¿los pedidos sin cobrar aparecen?), si hay filtros de fecha/rango, y si es una consulta en vivo o requiere una acción explícita de "cerrar" el período — estas ambiguidades son fáciles de pasar por alto porque no involucran escritura de datos, pero determinan si el número que ve el usuario es correcto o no.

No conviertas cada punto de esta lista en una pregunta automática — solo pregunta los que de verdad apliquen al módulo actual y no estén ya resueltos. El objetivo es criterio, no una checklist mecánica.

## Paso 3: generar `specs/00X-<nombre>/spec.md`

Con las respuestas del usuario, genera el archivo con esta estructura fija (mantenla siempre, en este orden):

```markdown
# Especificación: <nombre del módulo>

## Contexto y objetivo
<qué es este módulo y por qué existe, en 2-4 líneas>

## Usuarios
<roles que interactúan con esta funcionalidad>

## Historias de usuario
<formato "Como <rol>, quiero <acción>, para <beneficio>">

## Requisitos funcionales

### RF-1 — <nombre corto>
<uno o más criterios de aceptación en notación EARS, ver referencia abajo>

### RF-2 — <nombre corto>
...

## Requisitos no funcionales
<rendimiento, seguridad, disponibilidad, etc. — solo lo relevante a este módulo>

## Casos límite
<lista de casos borde ya resueltos con la respuesta del usuario>

## Fuera de alcance
<qué NO cubre esta spec, para no crear expectativas ni invadir otra spec>

## Criterios de finalización
<condiciones verificables que indican que esta spec está completamente implementada>

## Dudas abiertas
<cualquier punto que siga sin resolver, marcado como>
[NECESITA ACLARACIÓN]: <la pregunta pendiente>
```

### Referencia rápida: notación EARS en español

Usa siempre uno de estos patrones al escribir un criterio de aceptación — nunca prosa libre sin patrón:

- **Ubicuo** (siempre válido): "El sistema deberá siempre <acción>."
- **Basado en evento**: "Cuando <evento ocurre>, el sistema deberá <acción>."
- **Basado en estado**: "Mientras <estado activo>, el sistema deberá <acción>."
- **Condicional**: "Si <condición>, entonces el sistema deberá <acción>."
- **Característica opcional**: "Donde <característica presente>, el sistema deberá <acción>."

Cada RF puede tener varios criterios (varias líneas EARS), pero cada línea debe ser verificable con un test — si no se te ocurre cómo un test comprobaría esa línea, probablemente sigue siendo ambigua.

## Al terminar

Después de generar el archivo, dile al usuario en una o dos líneas qué preguntas quedaron marcadas como `[NECESITA ACLARACIÓN]` (si las hay) y recuérdale que el siguiente paso natural es la fase de clarificación (revisar la spec como un QA) antes de pasar a `plan.md` — pero no la ejecutes tú mismo, esa es una fase aparte.
