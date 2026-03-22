#!/bin/bash
# PhishCatcher — Full Docker Teardown & Fresh Start
# Run from the directory containing docker-compose.yml
# Usage: chmod +x docker_reset.sh && ./docker_reset.sh

set -e

echo ""
echo "========================================"
echo "  PhishCatcher — Full Docker Reset"
echo "========================================"

# -----------------------------------------------
# 1. Stop and remove all containers + networks
# -----------------------------------------------
echo ""
echo "--- Stopping containers ---"
docker compose down --remove-orphans
echo "[✓] Containers stopped and removed"

# -----------------------------------------------
# 2. Remove named volumes (all data wiped)
# -----------------------------------------------
echo ""
echo "--- Removing volumes ---"
docker volume rm phishcatcher_postgres_data 2>/dev/null && echo "[✓] Removed postgres_data" || echo "[~] postgres_data already gone"
docker volume rm phishcatcher_mongodb_data  2>/dev/null && echo "[✓] Removed mongodb_data"  || echo "[~] mongodb_data already gone"
docker volume rm phishcatcher_redis_data    2>/dev/null && echo "[✓] Removed redis_data"    || echo "[~] redis_data already gone"
docker volume rm phishcatcher_minio_data    2>/dev/null && echo "[✓] Removed minio_data"    || echo "[~] minio_data already gone"

# -----------------------------------------------
# 3. Remove project images (forces clean rebuild)
# -----------------------------------------------
echo ""
echo "--- Removing project images ---"
docker compose rm -f 2>/dev/null || true
IMAGES=$(docker compose images -q 2>/dev/null || true)
if [ -n "$IMAGES" ]; then
  echo "$IMAGES" | xargs docker rmi -f 2>/dev/null && echo "[✓] Images removed" || echo "[~] Some images skipped (in use elsewhere)"
else
  echo "[~] No project images to remove"
fi

echo ""
echo "========================================"
echo "  Stack fully removed."
echo ""
echo "  To bring it back up:"
echo "    docker compose up -d --build"
echo ""
echo "  Then run migrations:"
echo "    docker compose exec backend alembic upgrade head"
echo "========================================"
echo ""
