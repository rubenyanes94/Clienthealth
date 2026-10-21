# Infraestructura — Atención al Paciente

Documento de arquitectura e infraestructura para implementar el proyecto con Claude Code.
Producto: consola de atención al cliente para un centro médico (bandeja de WhatsApp, casos, hitos de
servicio e indicadores de satisfacción y tiempos). **No** gestiona agendas médicas ni citas.

> **Para Claude Code:** lee este documento completo antes de escribir código. Las secciones
> "Reglas" (§15) y "Plan por fases" (§14) son obligatorias. Si algo aquí contradice el código que ya
> existe en `backend/`, gana el código existente y señala la diferencia antes de cambiarla.
>
> Las diferencias entre este documento y lo implementado en las fases 0–1 están en **§17**.

---

## 1. Decisiones clave

| Tema | Decisión |
|---|---|
| Hosting | **Vercel**, un solo proyecto con **Vercel Services** (beta): servicio `web` (frontend) + servicio `api` (backend) en el mismo dominio |
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2 · Alembic · Pydantic Settings · psycopg 3 |
| Frontend | React + TypeScript · Vite · **Tailwind CSS v4** · React Router · TanStack Query |
| Base de datos | **Postgres en Neon** (integración de Vercel Marketplace), con rama de base de datos por cada preview |
| IA | Google Gemini (`google-genai`), solo como copiloto del agente y para sugerir el motivo |
| Mensajería | WhatsApp Cloud API oficial de Meta (webhook + Graph API). Modo simulación sin credenciales |
| Tiempo real | **Fase 1: polling** con TanStack Query. Fase 2 opcional: WebSockets de Vercel (beta) + Redis |
| Tareas programadas | Vercel Cron. El diseño no depende de crons frecuentes (ver §9) |
| Auth de agentes | JWT propio (`app/core/security.py`) entregado en **cookie httpOnly** |
| Métricas | Calculadas **siempre** desde `conversation_events` (registro de eventos inmutable) |
| Repo | Monorepo en GitHub: `frontend/` + `backend/` + `vercel.json` en la raíz |

---

## 2. Arquitectura

```
                         ┌───────────────────────── Vercel (1 proyecto) ─────────────────────────┐
 Agente (navegador) ───► │  Rewrites en vercel.json                                              │
                         │   /api/*  ──► servicio "api"  (FastAPI · Vercel Function · Fluid)      │──► Neon Postgres
                         │   /*      ──► servicio "web"  (Vite build estático en la CDN)          │      (pooled en runtime,
 Meta WhatsApp ────────► │   /api/webhooks/whatsapp ──► api                                      │       unpooled en migraciones)
                         │  Vercel Cron ──► /api/cron/* (Bearer CRON_SECRET)                     │
                         └───────────────────────────────────────────────────────────────────────┘
                                         │                         │
                                         ▼                         ▼
                              Graph API de Meta (envíos)    Gemini API (copiloto)
```

- Un solo dominio: el frontend llama a `/api/...` **sin CORS** y la cookie de sesión es del mismo
  origen.
- El servicio `api` recibe la ruta **completa**, con `/api` incluido. Todos los routers de FastAPI
  se montan bajo el prefijo `/api`.
- El backend es *serverless*: no hay procesos en segundo plano ni estado en memoria compartido entre
  peticiones. Todo lo que deba persistir va a Postgres.

---

## 3. Estructura del repositorio

`✅` = existe · `➕` = por crear

```
atencion-pacientes/
├── vercel.json                         ✅ servicios, rewrites, headers, crons
├── .devcontainer/                      ✅ Codespace: Python 3.12, Node 22, Postgres 16
├── docker-compose.yml                  ✅ Postgres 16 local (alternativa a Neon dev)
├── .github/workflows/ci.yml            ✅ lint + tests backend y frontend + tipos de la API
├── .env.example                        ✅ todas las variables de §10, sin valores reales
├── CLAUDE.md                           ✅ resumen corto de comandos y reglas
├── docs/
│   ├── INFRAESTRUCTURA.md              ✅ este documento
│   └── METRICAS.md                     ➕ diccionario oficial de indicadores (fase 3)
├── backend/
│   ├── pyproject.toml                  ✅ deps de runtime + [tool.vercel]
│   ├── .python-version                 ✅ 3.12
│   ├── alembic.ini · migrations/       ✅ env.py + versions/
│   ├── app/
│   │   ├── main.py                     ✅ crea FastAPI, monta routers bajo /api
│   │   ├── core/config.py · security.py✅
│   │   ├── db/base.py · session.py     ✅
│   │   ├── models/                     ✅ org.py, conversation.py, enums.py
│   │   ├── schemas/                    ✅ Pydantic de entrada/salida
│   │   ├── api/                        ✅ auth, inbox, conversations, admin, webhooks, ops (health,
│   │   │                                  metrics/live, cron, dev) · ➕ metrics, copilot
│   │   ├── api/deps.py                 ✅ current_agent, require_role
│   │   ├── services/                   ✅ events, conversations, whatsapp, outbound, inbound, bot,
│   │   │                                  urgency · ➕ surveys, copilot, metrics
│   │   └── seed.py                     ✅ áreas, motivos, FAQ y agente admin iniciales
│   ├── scripts/dump_openapi.py         ✅ OpenAPI sin levantar el servidor (CI)
│   └── tests/                          ✅ pytest sobre Postgres (fixtures de payloads de Meta)
└── frontend/
    ├── package.json · vite.config.ts   ✅
    └── src/
        ├── main.tsx · App.tsx · router.tsx · AppShell.tsx
        ├── styles.css                  ✅ @import "tailwindcss"; tokens con @theme, modo oscuro
        ├── api/schema.d.ts             ✅ generado desde el OpenAPI de FastAPI
        ├── api/client.ts · hooks.ts    ✅ openapi-fetch con credentials: "include"
        ├── features/inbox/             ✅ lista, chat, compositor, inspector, simulador
        ├── features/cases/             ✅ lista de casos y registro
        ├── features/metrics/           ➕ paneles e informes (fase 3)
        ├── features/auth/              ✅ login y guard de rutas
        └── components/ui/              ✅ botones, píldoras, segmentados, sheet, toast
```

---

## 4. `vercel.json` (raíz)

Ver el archivo real en la raíz del repo. Puntos clave:

- La regla de `/api/` va **antes** del comodín: Vercel aplica la primera regla que coincide. El
  servicio recibe la ruta original (`/api/health` llega como `/api/health`).
- El `rewrites` dentro de `web` es el fallback de la SPA, para que `/casos/123` sirva `index.html`.
- La migración **no** va en `buildCommand` del servicio `api`: va en `[tool.vercel.scripts] build`
  de `backend/pyproject.toml`, que según la documentación de FastAPI en Vercel se ejecuta *después*
  de instalar las dependencias. Un `buildCommand` en `vercel.json` tendría precedencia sobre ese
  script.
- `0 9 * * *` en UTC equivale a las 5:00 a. m. en Caracas.
- Services está en beta. **Validar con `vercel dev` y un deploy de preview** antes de construir
  encima: el Framework Preset del proyecto debe ser **Services** (`vercel project update --framework
  services`) y el Root Directory la raíz del repo. Verificar también que el cron enrute bien hacia
  `api` y que la clave de `functions` (`app/main.py`, relativa a la raíz del servicio) se aplique.
- Alternativa si Services da problemas: dos proyectos de Vercel en el mismo repo (`frontend/` y
  `backend/`) y un rewrite `/api/:path*` → dominio del backend en el proyecto del frontend. El código
  no cambia.

---

## 5. Backend

### 5.1 Restricciones serverless (obligatorias)

1. **Sin estado en memoria** entre peticiones: nada de diccionarios globales de sesiones, colas ni
   cachés de negocio.
2. **Conexiones**: `NullPool` + URL *pooled* de Neon en runtime (`db/session.py`). Alembic usa
   `DATABASE_URL_UNPOOLED`.
3. **Sin `BackgroundTasks` para trabajo crítico.** El webhook guarda primero y responde 200; si algo
   debe ocurrir sí o sí, debe ocurrir dentro de la petición o quedar registrado en la base para
   reintentarse.
4. **Tiempo de respuesta**: el webhook de Meta debe responder en menos de unos segundos. El flujo del
   bot es determinista y rápido. Gemini **nunca** se llama dentro del webhook, solo bajo demanda del
   agente.
5. **Archivos**: no escribir en disco. Si en el futuro se guardan adjuntos, usar Vercel Blob.
6. Toda fecha se guarda en UTC con `UTCDateTime`. La conversión a `America/Caracas` se hace solo al
   presentar y al calcular el horario hábil.

### 5.2 Capas

`api/` (routers: validan y llaman a servicios) → `services/` (reglas de negocio, transacciones,
`events.record(...)`) → modelos de SQLAlchemy. Los routers no contienen lógica de negocio y los
servicios no conocen HTTP.

Cada cambio de estado de un caso **debe** registrar su evento en `conversation_events` en la misma
transacción. Sin evento, la acción no cuenta en los indicadores.

### 5.3 Endpoints (todos bajo `/api`)

| Método y ruta | Uso |
|---|---|
| `GET /health` | Salud + verificación de la conexión a la base |
| `POST /auth/login` · `POST /auth/logout` · `GET /auth/me` | Sesión por cookie httpOnly |
| `GET /inbox?filter=&cursor=` | Bandeja (`open`, `queue`, `mine`, `pending`, `closed`, `bot`, `all`) |
| `GET /inbox/changes?since=<iso>` | Polling: IDs de conversaciones con cambios desde `since` |
| `GET /conversations/{id}` | Detalle + mensajes + eventos |
| `POST /conversations/{id}/accept` | Tomar un caso de la cola (o intervenir uno del bot, supervisor) |
| `POST /conversations/{id}/messages` | Responder (`is_internal_note` para notas internas) |
| `POST /conversations/{id}/pending` · `/resume` | Pausar y reanudar hitos (esperando al paciente) |
| `POST /conversations/{id}/transfer` | Cambiar de área (vuelve a cola) |
| `POST /conversations/{id}/close` | Cerrar: `contact_reason_id` obligatorio (+ CSAT en fase 2) |
| `POST /conversations/{id}/reopen` | Reabrir |
| `GET /catalog` | Áreas y motivos activos (cualquier agente; para transferir y cerrar) |
| `POST /copilot/{id}/summary` · `/suggest` · `/rewrite` · `/reason` | Copiloto Gemini (fase 2) |
| `GET /metrics/overview?from=&to=` · `/by-hour` · `/by-agent` · `/by-area` · `/reasons` · `/csat-daily` | Paneles (fase 3) |
| `GET /metrics/live` | Cola, urgentes, espera más antigua, agentes conectados |
| `GET/POST/PATCH /admin/areas` · `/admin/reasons` · `/admin/faqs` · `/admin/agents` | Catálogos (rol admin) |
| `GET /webhooks/whatsapp` | Verificación de Meta (`hub.verify_token`) |
| `POST /webhooks/whatsapp` | Mensajes entrantes y estados de entrega |
| `GET`/`POST /cron/daily-rollup` | Agregados diarios + detección de abandono |
| `POST /dev/simulate-inbound` | Inyecta un mensaje con formato Meta (supervisor; 404 en producción) |

### 5.4 Webhook de WhatsApp

1. Leer el **cuerpo crudo** (`await request.body()`) y validarlo con `verify_meta_signature`. Si
   falla, responder 401.
2. Idempotencia: `Message.external_id` (wamid) es único. Ante un duplicado, ignorar y responder 200.
3. Mensaje entrante: buscar o crear el `Contact` y la conversación abierta, o abrir una nueva. Si la
   última se cerró hace menos de `reopen_window_hours`, **reabrirla** y registrar `REOPENED`. Después
   ejecutar el clasificador de urgencia y luego el flujo del bot.
4. Respuesta a encuesta (botón o número): crear `SurveyResponse` y registrar `SURVEY_ANSWERED` (fase 2).
5. Estados (`sent`, `delivered`, `read`, `failed`): actualizar `Message.status` (solo hacia adelante;
   `failed` siempre se aplica).
6. Envíos salientes: respetar la ventana de 24 h. Fuera de ella solo se envían **plantillas
   aprobadas** (la encuesta CSAT es una plantilla).
7. Si `whatsapp_dry_run` es verdadero, no se llama a Meta; el mensaje queda con estado `SIMULATED`.
   Es el modo por defecto en local y en previews.
8. El webhook de Meta apunta **solo al dominio de producción**. Los previews tienen Deployment
   Protection y no reciben tráfico de Meta.

### 5.5 Clasificador de urgencia y bot

- Se ejecuta **antes** de cualquier flujo del bot. Fase 1: reglas con palabras y frases clave en
  español venezolano (dolor de pecho, no respira, sangrado, desmayo, convulsión…).
- Si hay urgencia: detener el bot, enviar el mensaje fijo de Emergencia (configurable con
  `EMERGENCY_MESSAGE`), marcar `is_urgent=True` y `priority=high`, y registrar `URGENCY_DETECTED`. El
  caso pasa al primer lugar de la cola.
- Bot de fase 1: máquina de estados determinista (menú → área → escalar). Las preguntas frecuentes se
  responden con textos fijos administrables (`/admin/faqs`). El bot **nunca** diagnostica ni
  recomienda medicamentos.

### 5.6 Copiloto (Gemini)

- Solo se invoca a pedido del agente. El agente siempre revisa y envía él mismo.
- El prompt **no** lleva el nombre, el teléfono ni la cédula del paciente: se sustituyen por
  `[PACIENTE]`. Solo se envían los últimos N mensajes necesarios.
- Usa un timeout corto (≈15 s) y, si falla, devuelve un error claro sin bloquear la conversación.
- El modelo se configura con `GEMINI_MODEL`.

---

## 6. Frontend

### 6.1 Stack

- **Vite + React + TypeScript** (modo estricto).
- **Tailwind CSS v4** con `@tailwindcss/vite`. Los tokens de diseño se definen en `@theme` dentro de
  `src/styles.css`, con soporte de modo oscuro.
- **React Router** para la navegación: `/conversaciones`, `/conversaciones/:id`, `/casos`,
  `/casos/:id`, `/paneles`, `/informes`, `/contactos`, `/login`.
- **TanStack Query** para el estado del servidor (caché, polling, invalidaciones).
- **openapi-typescript + openapi-fetch**: tipos generados desde `/api/openapi.json`. Script:
  `npm run gen:api`. Prohibido escribir a mano los tipos de la API.
- Gráficos: Recharts (fase 3). Íconos: lucide-react.
- Pruebas: Vitest + Testing Library. Calidad: ESLint + Prettier.

### 6.2 Desarrollo local

`vite.config.ts` hace proxy de `/api` → `http://localhost:8000`, así local y producción usan las
mismas rutas relativas. Alternativa: `vercel dev` en la raíz levanta ambos servicios igual que en
producción.

### 6.3 Sesión

Las peticiones usan `credentials: "include"`. Un `401` redirige a `/login`. No se guarda el token en
`localStorage`.

---

## 7. Base de datos y migraciones

- **Neon** instalado desde Vercel Marketplace en el proyecto. La integración inyecta `DATABASE_URL`
  (pooled) y `DATABASE_URL_UNPOOLED`. `config.py` normaliza `postgres://` y `postgresql://` a
  `postgresql+psycopg://`.
- **Ramas**: activar en la integración "crear rama de Neon por cada preview".
- **Alembic**:
  - `migrations/env.py` toma la URL de `get_settings().database_url_unpooled or database_url` e
    importa `app.models` para el autogenerate.
  - Siempre **revisar** el autogenerate antes de confirmarlo. Nunca editar una migración ya aplicada.
  - Patrón *expand → migrate → contract*: una migración no puede romper el código de la versión
    anterior, porque el despliegue migra antes de cambiar el tráfico.
- **Índices clave**: los de `conversation_events` (por conversación y fecha, por tipo y fecha).
- **SQLite**: solo para pruebas unitarias rápidas en local. Las pruebas y la CI corren sobre
  **Postgres**.

---

## 8. Tiempo real

**Fase 1 (MVP), polling:**

- Bandeja: `GET /inbox/changes?since=` cada **4 s** con la pestaña visible. Cuando hay cambios se
  invalidan la lista y la conversación abierta. Para un agente, el feed de cambios incluye los casos
  de su área tomados por otros, para que salgan de su cola.
- Conversación abierta: refresco cada 3 s.
- Los contadores de SLA corren **en el cliente** a partir de los timestamps del servidor.
- Es suficiente para un equipo de 5 a 15 agentes y funciona en cualquier plan de Vercel.

**Fase 2 (opcional):** WebSockets de Vercel Functions (beta) con reconexión automática y Redis
(Upstash) como pub/sub entre instancias. Implementarla solo si el polling se queda corto.

---

## 9. Tareas programadas

Límites de Vercel Cron: el plan **Hobby** solo permite una ejecución diaria, con precisión de ±59
min. **Pro** permite ejecuciones cada minuto. Por eso el diseño **no depende de crons frecuentes**:

| Necesidad | Solución sin cron frecuente |
|---|---|
| Encuesta CSAT | Se envía **dentro** de `POST /close`, respetando `survey_cooldown_days` |
| Reapertura | Se decide en el webhook, cuando el paciente vuelve a escribir |
| Abandono | `daily-rollup` registra `ABANDONED` en casos en cola sin respuesta humana tras `abandon_after_hours` (una vez por entrada en cola) |
| Agregados de paneles | `daily-rollup` diario |
| NPS mensual | `daily-rollup` comprueba si es el día configurado y envía a una muestra |

Los endpoints `/api/cron/*` exigen `Authorization: Bearer ${CRON_SECRET}` y son **idempotentes**.

> **Plan de Vercel:** Hobby sirve para desarrollar. Para operar con un centro médico real se necesita
> **Pro**: el plan Hobby es de uso personal y no comercial.

---

## 10. Variables de entorno

| Variable | Dónde | Notas |
|---|---|---|
| `DATABASE_URL` | Neon (auto) | Pooled. En local: Postgres del docker-compose o rama dev de Neon |
| `DATABASE_URL_UNPOOLED` | Neon (auto) | Para Alembic |
| `ENVIRONMENT` | Manual | `development` · `preview` · `production` |
| `JWT_SECRET` | Manual | 64+ caracteres aleatorios, distinto por entorno. La app no arranca en preview/producción sin él |
| `JWT_EXPIRE_MINUTES` | Opcional | Por defecto 720 |
| `WHATSAPP_VERIFY_TOKEN` | Manual | El mismo que se configura en Meta |
| `WHATSAPP_APP_SECRET` | Manual | Para validar la firma del webhook |
| `WHATSAPP_ACCESS_TOKEN` | Manual (solo prod) | Token de usuario del sistema. Vacío = simulación |
| `WHATSAPP_PHONE_NUMBER_ID` | Manual (solo prod) | |
| `WHATSAPP_GRAPH_VERSION` | Opcional | Por defecto `v23.0` |
| `WHATSAPP_FORCE_DRY_RUN` | Opcional | `true` fuerza simulación aunque haya credenciales |
| `EMERGENCY_MESSAGE` | Opcional | Texto oficial de Emergencia (pendiente de aprobación, §16) |
| `GEMINI_API_KEY` | Manual | |
| `GEMINI_MODEL` | Opcional | Por defecto `gemini-2.5-flash` |
| `CRON_SECRET` | Manual | Vercel lo envía como Bearer a los crons |
| `TIMEZONE` | Opcional | `America/Caracas` |

En local: `vercel env pull .env` o copiar `.env.example`. **Nunca** se suben `.env` al repo.

---

## 11. Entornos y CI/CD

| Entorno | Disparador | Base de datos | WhatsApp |
|---|---|---|---|
| Local / Codespace | `vercel dev` o `uvicorn` + `vite` | Postgres local o rama dev de Neon | Simulación |
| Preview | Cada PR (Vercel Git) | Rama de Neon del PR | Simulación |
| Producción | Merge a `main` | Rama principal de Neon | Real |

**GitHub Actions** (`ci.yml`, en cada PR):

1. Backend: `ruff check`, `ruff format --check`, `alembic upgrade head` + `alembic check` +
   `alembic downgrade base` sobre una base vacía, y `pytest` contra Postgres 16.
2. Frontend: `npm ci`, `npm run lint`, `tsc --noEmit`, `npm test`, `npm run build`.
3. Tipos de la API: regenerar `schema.d.ts` y fallar si hay diferencias sin confirmar.

El despliegue lo hace la integración de Git de Vercel, no GitHub Actions.

---

## 12. Seguridad y privacidad

Las conversaciones contienen datos de salud, así que estas reglas aplican a todo el código.

- **Logs**: prohibido registrar el texto de los mensajes, teléfonos, cédulas o diagnósticos. Solo se
  loguean IDs internos y tipos de evento.
- `ConversationEvent.data` nunca contiene texto del paciente (hay una prueba que lo verifica).
- **Roles**: `agent` ve la cola de su área y sus casos; `supervisor` ve todo (incluidas las
  conversaciones del bot) y los paneles; `admin` además gestiona catálogos y agentes. Se verifica en
  el backend, nunca solo en la interfaz.
- **Cookie de sesión**: `HttpOnly`, `Secure`, `SameSite=Strict`, con `Path=/`.
- **Rate limit** en `/auth/login`, mediante el Firewall de Vercel o una regla simple en la base (fase 4).
- **Encabezados de seguridad** en el servicio `web`: `Content-Security-Policy`,
  `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`.
- **Consentimiento**: `Contact.opt_in_at` es obligatorio para enviar plantillas proactivas, como el NPS.
- **Gemini**: datos seudonimizados (§5.6). No se usa para decidir urgencias.
- **Secretos** solo en las variables de entorno de Vercel.
- Antes de producción: revisión legal del manejo de datos de salud (habeas data y secreto médico en
  Venezuela) y una política de retención de mensajes.

---

## 13. Observabilidad

- **Logs** de Vercel con formato estructurado (`event`, `conversation_id`, `duration_ms`).
- `GET /api/health` se puede vigilar con un monitor externo cada 5 minutos.
- Errores: Sentry (opcional, fase 4), con el filtrado de datos personales activado.
- Las métricas de negocio salen de la propia base de datos.

---

## 14. Plan por fases

Cada fase termina con sus pruebas en verde y un deploy de preview funcionando.

**Fase 0 — Esqueleto desplegable** ✅ (pendiente: validar el deploy de preview en Vercel)

**Fase 1 — Bandeja y casos** ✅
- Auth, webhook (verificación, firma, idempotencia, estados), servicio de conversaciones con eventos,
  clasificador de urgencia, bot determinista, bandeja, casos, registro y polling.
- ✔ Criterio verificado: un mensaje simulado entra por el webhook, aparece en la bandeja y un agente
  lo acepta, responde y cierra, con los eventos completos.

**Fase 2 — Encuestas y copiloto**
- CSAT al cierre (plantilla, cooldown, captura de la respuesta) y NPS mensual por muestreo.
- Endpoints del copiloto con seudonimización y su panel en el frontend.

**Fase 3 — Indicadores**
- `docs/METRICAS.md` con la fórmula exacta de cada KPI: 1ª respuesta, SLA, CSAT, NPS, FCR, contención
  del bot, abandono, resolución, reapertura y transferencias.
- Calendario hábil por área y feriados (tabla + servicio de "minutos hábiles entre dos fechas").
- Endpoints `/metrics/*`, agregados en `daily-rollup` y los paneles e informes del frontend.
- ✔ Criterio: pruebas con escenarios de eventos fijos que comparan cada KPI con el valor esperado,
  incluidas pausas, fuera de horario y reaperturas.

**Fase 4 — Endurecimiento**
- Rate limits, Sentry, auditoría de accesos a conversaciones, exportación a Excel y, opcionalmente,
  WebSockets.

---

## 15. Reglas para Claude Code

1. Los routers van bajo `/api`. El frontend solo usa rutas relativas `/api/...`.
2. No se introducen procesos persistentes, colas en memoria, Celery ni Redis en las fases 0–3.
3. Todo cambio de estado de un caso registra su evento en la misma transacción.
4. Las fechas en UTC usan `utcnow()` y `UTCDateTime`. Nunca `datetime.now()` sin zona horaria.
5. No se loguea ni se envía a Gemini texto identificable del paciente.
6. Las dependencias de runtime van en `[project.dependencies]` y las de desarrollo en
   `[project.optional-dependencies].dev`. Vercel instala solo las de runtime.
7. Los tipos de la API se regeneran con `npm run gen:api` después de cambiar schemas del backend.
8. Antes de terminar una tarea: `ruff check`, `pytest`, `npm run lint`, `tsc --noEmit` y
   `npm run build`.
9. Ante una duda de configuración de Vercel (Services está en beta), consulta su documentación
   actual en lugar de suponer, y valida con `vercel dev` o un deploy de preview.

---

## 16. Pendientes por confirmar con el centro médico

- Lista definitiva de áreas, metas de SLA por área y horario hábil, incluidos los sábados.
- Catálogo inicial de motivos de contacto (el seed actual es provisional).
- Texto oficial del mensaje de Emergencia y lista de palabras de urgencia.
- Textos de las preguntas frecuentes del bot (el horario del seed es un marcador provisional).
- Número de WhatsApp Business, verificación del negocio en Meta y plantillas (CSAT, NPS, reapertura).
- Canales de la fase 1: ¿solo WhatsApp, o también Instagram y web?
- Plan de Vercel (Pro para producción) y región de la base de Neon (la más cercana: `us-east`).

---

## 17. Notas de implementación (fases 0–1)

Diferencias con la versión original de este documento y su motivo:

1. **El repo partía vacío.** La versión original marcaba `backend/` como existente; se creó desde
   cero siguiendo el diseño descrito.
2. **Migración en el build**: se movió de `buildCommand` (en `vercel.json`) a
   `[tool.vercel.scripts] build` en `pyproject.toml`, que la documentación de Vercel garantiza que
   corre después de instalar las dependencias. `functions` usa la clave del archivo de entrada
   (`app/main.py`) en lugar de `**/*`.
3. **Estados de la conversación**: `bot` → `queued` → `open` ⇄ `pending` → `closed`. `Area.is_default`
   marca el área a la que el bot deriva por defecto (y las urgencias).
4. **Endpoints añadidos**: `GET /catalog` (los agentes necesitan áreas y motivos sin ser admin),
   `/admin/faqs` (textos del bot administrables) y `POST /dev/simulate-inbound` (probar sin Meta).
5. **Contención del bot**: cuando el paciente confirma que la FAQ resolvió su duda, el bot cierra la
   conversación y registra `BOT_RESOLVED` + `CLOSED {by: "bot"}`.
6. **Errores del bot**: si la automatización falla tras guardar el mensaje entrante, la conversación
   se deriva a la cola (`BOT_ESCALATED {reason: "bot_error"}`) para que un humano la vea.
7. **TypeScript 5.9** en lugar de 7.x: typescript-eslint y openapi-typescript aún no admiten la 7.
8. **Pendiente de Fase 0**: validar el deploy de preview en Vercel (requiere la cuenta del proyecto).
