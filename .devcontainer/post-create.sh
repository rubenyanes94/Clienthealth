#!/usr/bin/env bash
# Se ejecuta una vez al crear (o reconstruir) el Codespace: dependencias, .env, base y datos de prueba.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Backend: entorno de Python"
# --clear: el .venv vive en /workspaces y sobrevive a los rebuilds; uno creado con otra imagen no sirve.
python -m venv --clear backend/.venv
backend/.venv/bin/pip install -q --upgrade pip
backend/.venv/bin/pip install -q -e 'backend[dev]'

echo "==> Frontend: dependencias"
(cd frontend && npm ci --no-audit --no-fund)

if [ ! -f backend/.env ]; then
  echo "==> backend/.env desde .env.example (secretos aleatorios)"
  cp .env.example backend/.env
  secret() { backend/.venv/bin/python -c "import secrets; print(secrets.token_urlsafe($1))"; }
  sed -i "s|^JWT_SECRET=.*|JWT_SECRET=$(secret 64)|" backend/.env
  sed -i "s|^CRON_SECRET=.*|CRON_SECRET=$(secret 32)|" backend/.env
fi

cd backend
echo "==> Migraciones"
.venv/bin/alembic upgrade head

# Credenciales del admin: secretos de Codespaces ADMIN_EMAIL/ADMIN_PASSWORD, o las de desarrollo.
export ADMIN_EMAIL="${ADMIN_EMAIL:-admin@local.test}"
export ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin12345}"
.venv/bin/python -m app.seed
.venv/bin/python -m scripts.demo_data

echo
echo "Listo. Admin: $ADMIN_EMAIL (contraseña: la de ADMIN_PASSWORD, o admin12345 si no se definió)."
