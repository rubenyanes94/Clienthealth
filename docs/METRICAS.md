# Diccionario de indicadores

Definición oficial de cada KPI de la consola. La implementación está en
`backend/app/services/metrics.py` y cada fórmula tiene su prueba con escenarios fijos en
`backend/tests/test_metrics_kpis.py`. Si se cambia una definición aquí, se cambian también el código
y la prueba.

## Principios

- **Fuente única**: todo se calcula desde `conversation_events` (y `surveys` para las encuestas), y
  los indicadores de la sala desde `case_events`.
  Si una acción no registró su evento, no existe para los indicadores.
- **Minutos hábiles**: los tiempos se miden en minutos dentro del horario hábil del área
  (tabla `business_hours`), sin contar feriados (`holidays`), en hora de Caracas. Un área sin
  horario propio usa el horario por defecto; sin ningún horario configurado se usan minutos de reloj.
- **Pausas**: el tiempo con el caso *en espera del paciente* (`PENDING_STARTED` → `PENDING_RESUMED`
  o cierre) se descuenta de los tiempos de atención.
- **Período**: `from` y `to` son fechas locales (Caracas), ambas incluidas. Cada indicador indica
  qué fecha lo ubica en el período.
- **Sin datos**: si el denominador es 0, el valor es `null` (la interfaz muestra «—»), nunca 0 %.
- **Proporciones** se devuelven como `{value, numerator, denominator}` para poder auditarlas.

## Episodio de atención

Un **episodio** es un tramo de atención humana de una conversación. Una conversación puede tener
varios (por ejemplo, si se cierra y el paciente vuelve a escribir).

| Empieza con | Origen |
|---|---|
| `BOT_ESCALATED` (el bot o una urgencia deriva a la cola) | `queue` |
| `REOPENED` por el paciente que vuelve a la cola (`status: queued`) | `queue` |
| `ACCEPTED` con `from_status: bot` (un supervisor interviene al bot) | `intervention` |
| `REOPENED` por un agente (`status: open`) | `agent_reopen` |

Termina con `CLOSED`. Su **área** es la del momento en que entra en cola: las transferencias no la
cambian (se cuentan aparte). Un episodio pertenece al período por la **fecha en que empieza**.

Los episodios `agent_reopen` los inicia el propio agente, por eso no cuentan para la primera
respuesta, el SLA ni el abandono.

## Indicadores

### Volumen
- **Conversaciones**: conversaciones con `CREATED` en el período.
- **Episodios**: episodios que empiezan en el período.
- **Urgencias**: eventos `URGENCY_DETECTED` en el período.

### Tiempo de primera respuesta (FRT)
Minutos hábiles desde el inicio del episodio hasta el primer `AGENT_MESSAGE` con estado distinto de
`failed`, descontando pausas. Se informan el promedio, la mediana y el p90 (rango más cercano).
Solo episodios con respuesta y origen distinto de `agent_reopen`.

### Cumplimiento de SLA
`cumplen / (cumplen + incumplen)`, con meta = `areas.sla_first_response_minutes` del área del episodio.
- **Cumple**: FRT ≤ meta.
- **Incumple**: FRT > meta, **o** sigue sin respuesta y ya lleva más minutos hábiles que la meta.
- **Excluido**: sigue sin respuesta pero dentro de plazo, o se cerró sin respuesta humana (spam,
  duplicado), o es `agent_reopen`.

### Tiempo de resolución
Minutos hábiles desde el inicio del episodio hasta su `CLOSED` por un agente, descontando pausas.
Promedio, mediana y p90.

### Tasa de resolución
`episodios cerrados (por agente o bot) / episodios`.

### Resolución al primer contacto (FCR)
Entre los episodios cerrados por un agente: `sin transferencias y sin reapertura dentro de
REOPEN_WINDOW_HOURS / episodios evaluables`.
- No es FCR si tuvo alguna `TRANSFERRED` o si un `REOPENED` llegó antes de que venciera la ventana.
- Es FCR si no tuvo transferencias y la ventana ya venció sin reapertura.
- **Pendiente** (fuera del cálculo) mientras la ventana no haya vencido y no haya otro motivo para
  descartarlo. Por eso el FCR de «hoy» suele tener un denominador pequeño.

### Tasa de reapertura
`episodios cerrados por agente que se reabrieron dentro de la ventana / episodios cerrados por agente`.

### Tasa de transferencia
`episodios con al menos un TRANSFERRED / episodios`.

### Tasa de abandono
`episodios abandonados / episodios (sin agent_reopen)`. Un episodio está abandonado si nunca tuvo
respuesta humana y además tiene el evento `ABANDONED` (lo registra `daily-rollup`) **o** sigue abierto
y lleva `ABANDON_AFTER_HOURS` horas de reloj desde que empezó (cálculo al vuelo para «hoy»).

### Contención del bot
`conversaciones resueltas por el bot (BOT_RESOLVED) que nunca tuvieron un episodio humano /
conversaciones`. Con filtro de área no aplica (el bot no tiene área) y vale `null`.

### CSAT
Encuestas CSAT (1–5) **respondidas** en el período (fecha de respuesta).
- **Promedio**: media de las puntuaciones.
- **% satisfechos**: `respuestas con 4 o 5 / respuestas`.
- **Tasa de respuesta**: `respondidas en el período / (respondidas + enviadas sin respuesta en el
  período)`. Los envíos fallidos no cuentan.
- Por agente: la del agente que cerró el caso. Por área: el área de la conversación.

### NPS
Encuestas NPS (0–10) respondidas en el período. Promotores 9–10, pasivos 7–8, detractores 0–6.
`NPS = 100 × (promotores − detractores) / respuestas`, de −100 a 100.

## Desgloses

| Endpoint | Agrupa por | Notas |
|---|---|---|
| `/metrics/by-hour` | Hora local de inicio del episodio | Incluye mensajes entrantes por hora (`INBOUND_MESSAGE`) |
| `/metrics/by-area` | Área del episodio | Mismos KPI que el resumen |
| `/metrics/by-agent` | Agente | Aceptados (`accepted_by`), FRT de quien respondió primero, resolución, FCR y CSAT de quien cerró |
| `/metrics/reasons` | Motivo de cierre | Cierres por agente con **fecha de cierre** en el período |
| `/metrics/csat-daily` | Día local de respuesta | Todos los días del período, con `null` si no hubo respuestas |

## Rendimiento

Los indicadores se calculan al vuelo cargando los eventos de las conversaciones con actividad en el
período. Es suficiente para el volumen esperado (miles de conversaciones al mes). Si los paneles se
vuelven lentos, `daily-rollup` puede guardar contadores diarios por área (numeradores y
denominadores, no porcentajes) sin cambiar estas definiciones.

## Sala en tiempo real (módulo de Casos)

Implementación en `backend/app/services/cases.py` (`live`) y pruebas en
`backend/tests/test_patients_cases.py`. A diferencia del resto de este documento, se miden en
**minutos de reloj**: quien espera en la sala espera igual fuera del horario hábil. «Hoy» es el día
local de Caracas.

| Indicador | Definición |
|---|---|
| Registrado, En atención, En espera, Resuelto | Casos que están ahora en esa etapa, en total y por área |
| Urgentes | Casos no cerrados con prioridad alta |
| Espera más larga | Tiempo desde `stage_changed_at` del caso *Registrado* más antiguo. Transferir reinicia el conteo |
| Fuera de meta | Casos *Registrados* que llevan en su área al menos `sla_first_response_minutes` |
| Creados hoy / Cerrados hoy | Casos con `opened_at` / `closed_at` en el día |
| 1ª atención (mediana) | Casos abiertos hoy: desde la apertura hasta su primer `STAGE_CHANGED` a `in_progress`. Los aún no atendidos no cuentan |
| Resolución (mediana) | Casos con `resolved_at` hoy: desde la apertura hasta `resolved_at`, descontando el tiempo en *En espera*. Si se reabrió, el tiempo entre medias cuenta |
