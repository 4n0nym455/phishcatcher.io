#!/usr/bin/env bash
# PhishCatcher Quick Start Script
# Backend & Frontend run locally, Services run in Docker.

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$PROJECT_DIR/phishcatcher-backend/docker-compose.yml"
ENV_FILE="$PROJECT_DIR/phishcatcher-backend/.env"
COMPOSE="docker compose"

# ── Cleanup on exit ──────────────────────────────────────────────────────────────

PIDS=()

cleanup() {
  echo ""
  echo "🛑 Shutting down..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down >/dev/null 2>&1 || true
  exit 0
}

trap cleanup SIGINT SIGTERM

compose() {
  $COMPOSE "$@"
}

# ── Pre-flight ───────────────────────────────────────────────────────────────────

if ! docker info >/dev/null 2>&1; then
  echo "❌ Docker is not running."
  exit 1
fi

if ! command -v docker compose &>/dev/null; then
  echo "❌ docker compose (v2) is not installed."
  exit 1
fi

if ! command -v python3 &>/dev/null; then
  echo "❌ python3 not found."
  exit 1
fi

if ! command -v npm &>/dev/null; then
  echo "❌ npm not found."
  exit 1
fi

echo "🚀 Starting PhishCatcher Development Environment..."

# Load env variables for local commands (compose already gets them via --env-file)
if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

# ── Docker infrastructure ────────────────────────────────────────────────────────

echo "📁 Creating directories..."
mkdir -p phishcatcher-backend/logs

echo "🐳 Starting Docker services..."
compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d postgres mongodb redis minio

# Wait for services with health checks
echo "⏳ Waiting for services..."
wait_for_postgres() {
  for i in $(seq 1 30); do
    if docker exec phishcatcher-postgres pg_isready -U "${POSTGRES_USER:-phishcatcher}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

wait_for_mongo() {
  for i in $(seq 1 30); do
    if docker exec phishcatcher-mongodb mongosh --quiet --eval "db.runCommand({ping:1})" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

wait_for_redis() {
  for i in $(seq 1 30); do
    if docker exec phishcatcher-redis redis-cli -a "${REDIS_PASSWORD:-redis_secret}" --no-auth-warning ping 2>/dev/null | grep -q PONG; then
      return 0
    fi
    sleep 1
  done
  return 1
}

wait_for_postgres && echo "  ✅ PostgreSQL ready" || echo "  ⚠️  PostgreSQL timed out"
wait_for_redis   && echo "  ✅ Redis ready"     || echo "  ⚠️  Redis timed out"
wait_for_mongo   && echo "  ✅ MongoDB ready"   || echo "  ⚠️  MongoDB timed out"

# Create MinIO buckets
echo "🪣 Creating MinIO buckets..."
docker exec phishcatcher-minio mc alias set local http://localhost:9000 "${MINIO_ACCESS_KEY:-minioadmin}" "${MINIO_SECRET_KEY:-minioadmin}" 2>/dev/null || true
for bucket in "${MINIO_BUCKET_EMAILS:-phishcatcher-emails}" \
              "${MINIO_BUCKET_REPORTS:-phishcatcher-reports}" \
              "${MINIO_BUCKET_MODELS:-phishcatcher-models}" \
              "${MINIO_BUCKET_AVATARS:-phishcatcher-avatars}"; do
  docker exec phishcatcher-minio mc mb "local/$bucket" 2>/dev/null || true
done

# ── Backend ──────────────────────────────────────────────────────────────────────

echo "🔧 Setting up backend..."
cd phishcatcher-backend

if [ ! -f ".env" ]; then
  if [ -f "$ENV_FILE" ]; then
    cp "$ENV_FILE" .env
    echo "  ✅ Copied .env"
  else
    echo "❌ No .env file. Create phishcatcher-backend/.env first."
    exit 1
  fi
fi

if [ ! -d ".venv" ]; then
  echo "🐍 Creating virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate

echo "📦 Installing Python dependencies..."
pip install -q -r requirements.txt

echo "🗃️  Running migrations..."
alembic upgrade head 2>/dev/null || {
  echo "  ⚠️  Schema exists without alembic tracking — resetting..."
  docker exec phishcatcher-postgres psql -U "${POSTGRES_USER:-phishcatcher}" -d "${POSTGRES_DB:-phishcatcher}" -c "
    DROP SCHEMA public CASCADE;
    CREATE SCHEMA public;
  " >/dev/null 2>&1
  alembic upgrade head
}

echo "👤 Creating admin user (skip if exists)..."
PYTHONPATH=. python scripts/create_admin.py || echo "  Admin creation skipped"

# ── Start backend ────────────────────────────────────────────────────────────────

echo "🚀 Starting backend (port 8000)..."
source .venv/bin/activate
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
PIDS+=($!)

echo "🚀 Starting Celery worker..."
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4 &
PIDS+=($!)

# ── Frontend ─────────────────────────────────────────────────────────────────────

echo "🎨 Setting up frontend..."
cd "$PROJECT_DIR/phishcatcher-frontend/app"

if [ ! -d "node_modules" ]; then
  echo "📦 Installing Node.js dependencies..."
  npm install
fi

if [ ! -f ".env.local" ]; then
  echo "📝 Creating .env.local..."
  cat > .env.local << 'EOF'
VITE_API_URL=https://phishcatcher.dpdns.org/api/v1
VITE_WS_URL=wss://phishcatcher.dpdns.org/ws
EOF
fi

echo "🚀 Building frontend..."
npm run build

echo "🚀 Starting frontend preview (port 4173)..."
npm run preview -- --host &
PIDS+=($!)

# ── Ready ────────────────────────────────────────────────────────────────────────

echo ""
echo "🎉 PhishCatcher is ready!"
echo ""
echo "📋 Services:"
echo "   Docker infrastructure:"
echo "     • PostgreSQL : localhost:5432"
echo "     • MongoDB    : localhost:27017"
echo "     • Redis      : localhost:6379"
echo "     • MinIO API  : http://localhost:9000"
echo "     • MinIO UI   : http://localhost:9001"
echo ""
echo "   Local development:"
echo "     • Frontend  : http://localhost:4173"
echo "     • Backend   : http://localhost:8000"
echo "     • API Docs  : http://localhost:8000/docs"
echo ""
echo "🛑 Press Ctrl+C to stop all services"

# Wait for any process to exit
wait
