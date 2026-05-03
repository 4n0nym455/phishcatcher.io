#!/usr/bin/env bash
# PhishCatcher Docker Reset Script
# Stops containers, removes volumes, and flushes all databases.

set -e

COMPOSE="docker compose"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$PROJECT_DIR/phishcatcher-backend/docker-compose.yml"
ENV_FILE="$PROJECT_DIR/phishcatcher-backend/.env"

# ── Helpers ──────────────────────────────────────────────────────────────────────

load_env() {
  if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
  fi
}

compose() {
  $COMPOSE --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

# ── Main ─────────────────────────────────────────────────────────────────────────

echo "🧹 Resetting PhishCatcher Docker environment..."

# Check Docker
if ! docker info >/dev/null 2>&1; then
  echo "❌ Docker is not running."
  exit 1
fi

# Load env for credentials
load_env

# Stop & remove containers
echo "📦 Stopping and removing containers..."
compose down --remove-orphans 2>/dev/null || true

# Flush databases before removing volumes (in case they need a clean start)
echo "🗃️  Flushing PostgreSQL..."
docker exec phishcatcher-postgres psql -U "${POSTGRES_USER:-phishcatcher}" -d "${POSTGRES_DB:-phishcatcher}" -c "
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO ${POSTGRES_USER:-phishcatcher};
" 2>/dev/null || true

echo "🗃️  Flushing MongoDB..."
docker exec phishcatcher-mongodb mongosh -u "${MONGO_USER:-phishcatcher}" -p "${MONGO_PASSWORD:-changeme}" --authenticationDatabase admin --quiet --eval "
db.getSiblingDB('${MONGO_DB:-phishcatcher}').getCollectionNames().forEach(function(c) {
  db.getSiblingDB('${MONGO_DB:-phishcatcher}').getCollection(c).drop();
});
" 2>/dev/null || true

echo "🗃️  Flushing Redis..."
docker exec phishcatcher-redis redis-cli -a "${REDIS_PASSWORD:-redis_secret}" --no-auth-warning FLUSHDB 2>/dev/null || true

# Remove volumes
echo "🗑️  Removing volumes..."
compose down --volumes --remove-orphans 2>/dev/null || true
docker volume ls -q | grep -E "phishcatcher|postgres_data|mongodb_data|redis_data|minio_data" | xargs -r docker volume rm 2>/dev/null || true

# Remove networks
echo "🧽 Removing networks..."
docker network ls -q | grep phishcatcher | xargs -r docker network rm 2>/dev/null || true

# Prune orphans
docker container prune -f >/dev/null 2>&1 || true

echo ""
echo "✅ Docker environment has been reset!"
echo ""
echo "To start fresh, run:"
echo "   ./setup.sh"
