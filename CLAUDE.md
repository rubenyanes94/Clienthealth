# Atención al Paciente — Centro Médico San Bernardino

Consola de atención al paciente (casos entre áreas, pacientes, bandeja de WhatsApp, bot, indicadores). Se enfoca solo en la atención: pivotea requerimientos entre áreas y mejora la comunicación con el paciente. **No** es un sistema clínico ni gestiona citas.
Cómo se usa cada pantalla (para el personal) está en [docs/MANUAL_USUARIO.md](docs/MANUAL_USUARIO.md).
La arquitectura, reglas y plan por fases están en [docs/INFRAESTRUCTURA.md](docs/INFRAESTRUCTURA.md):
léelo antes de cambiar algo estructural. Las reglas de §15 son obligatorias.

## Comandos

En el Codespace todo arranca solo (API :8000, web :5173, logs en `/tmp/atencion/`).
Para reiniciar ambos servidores: `bash .devcontainer/start.sh`.

```bash
docker compose up -d db                       # Postgres 16 local (crea también atencion_test)

# Backend (Python 3.12)
cd backend
cp ../.env.example .env                       # y completa JWT_SECRET, etc.
.venv/bin/alembic upgrade head
ADMIN_EMAIL=... ADMIN_PASSWORD=... .venv/bin/python -m app.seed
.venv/bin/uvicorn app.main:app --reload --port 8000
.venv/bin/python -m scripts.demo_data          # 14 días de datos ficticios para los paneles
.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/pytest -q

# Frontend
cd frontend
npm run dev                                   # http://localhost:5173 (proxy /api → :8000)
npm run gen:api                               # tras cambiar schemas del backend (con la API arriba)
npm run lint && npx tsc -b --noEmit && npm test && npm run build
```

## Reglas rápidas

- Routers bajo `/api`; el frontend solo usa rutas relativas `/api/...`. Tipos de la API generados, nunca a mano.
- Todo cambio de estado llama a `events.record(...)` (conversaciones) o `events.record_case(...)` (casos) en la misma transacción.
- Un *caso* (`Case`, módulo de Casos) no es una *conversación* (chat de WhatsApp): ver §20 de la infraestructura.
- Si cambias un flujo o un texto de la interfaz, actualiza [docs/MANUAL_USUARIO.md](docs/MANUAL_USUARIO.md).
- Los KPI se definen en [docs/METRICAS.md](docs/METRICAS.md); si cambias una fórmula, cambia el doc y su prueba.
- Fechas: `utcnow()` y `UTCDateTime`. Nunca `datetime.now()` sin zona.
- Prohibido loguear o mandar a Gemini texto, nombres, teléfonos o cédulas de pacientes.
- Serverless: nada de estado en memoria, colas propias ni `BackgroundTasks` para trabajo crítico.
- Para probar sin Meta: botón «Simular» en la bandeja (supervisor/admin, fuera de producción).
