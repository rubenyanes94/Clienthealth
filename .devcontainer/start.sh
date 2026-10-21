#!/usr/bin/env bash
# Se ejecuta cada vez que arranca el Codespace: migra y levanta la API (:8000) y la web (:5173).
# Logs en /tmp/atencion/{api,web}.log. Para reiniciar a mano: bash .devcontainer/start.sh
set -euo pipefail
cd "$(dirname "$0")/.."
LOGS=/tmp/atencion
mkdir -p "$LOGS"

# Si se cambió de rama, puede haber migraciones nuevas.
(cd backend && .venv/bin/alembic upgrade head)

# Cada servidor corre en su propio grupo de procesos (setsid) y su PID queda en $LOGS/<nombre>.pid.
# setsid + nohup: siguen vivos cuando termina el comando de arranque del contenedor.
launch() {
  local name=$1 dir=$2
  shift 2
  # Un reinicio a mano detiene antes la instancia anterior (el grupo completo: reloader, npm, vite).
  if [ -f "$LOGS/$name.pid" ]; then
    kill -- "-$(cat "$LOGS/$name.pid")" 2>/dev/null || true
    sleep 1
  fi
  (cd "$dir" && exec setsid nohup "$@" >"$LOGS/$name.log" 2>&1 </dev/null) &
  echo $! >"$LOGS/$name.pid"
}

launch api backend .venv/bin/uvicorn app.main:app --reload --port 8000
launch web frontend npm run dev

echo "API en http://localhost:8000 · web en http://localhost:5173 · logs en $LOGS"
