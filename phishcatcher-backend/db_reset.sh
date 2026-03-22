#!/bin/bash
# PhishCatcher — Database Reset & Migration Script
# Run from: phishcatcher-backend/
# Usage:    chmod +x db_reset.sh && ./db_reset.sh

set -e  # exit on first error

echo ""
echo "========================================"
echo "  PhishCatcher DB Reset"
echo "========================================"

# -----------------------------------------------
# 1. Load environment
# -----------------------------------------------
if [ -f ".env" ]; then
  export $(grep -v '^#' .env | xargs)
  echo "[✓] Loaded .env"
else
  echo "[!] No .env found — using defaults"
  export POSTGRES_USER=${POSTGRES_USER:-postgres}
  export POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
  export POSTGRES_HOST=${POSTGRES_HOST:-localhost}
  export POSTGRES_PORT=${POSTGRES_PORT:-5432}
  export POSTGRES_DB=${POSTGRES_DB:-phishcatcher}
fi

DB_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"

# -----------------------------------------------
# 2. Check PostgreSQL is reachable
# -----------------------------------------------
echo ""
echo "--- Checking PostgreSQL ---"

if ! command -v pg_isready &> /dev/null; then
  echo "[!] pg_isready not found — trying pg_isready from pg_wrapper"
fi

# Try connecting; if it fails, start PostgreSQL
pg_isready -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" 2>/dev/null
PG_STATUS=$?

if [ $PG_STATUS -ne 0 ]; then
  echo "[!] PostgreSQL not running. Attempting to start..."

  # Try common init methods in order
  if command -v pg_ctlcluster &> /dev/null; then
    # Debian/Ubuntu with pg_wrapper (your environment)
    PG_VERSION=$(pg_lsclusters -h | awk 'NR==1{print $1}' 2>/dev/null || echo "")
    PG_CLUSTER=$(pg_lsclusters -h | awk 'NR==1{print $2}' 2>/dev/null || echo "main")

    if [ -z "$PG_VERSION" ]; then
      echo "[✗] No PostgreSQL cluster found. Install or init one first:"
      echo "    sudo apt install postgresql"
      echo "    sudo pg_createcluster 16 main --start"
      exit 1
    fi

    echo "    pg_ctlcluster ${PG_VERSION} ${PG_CLUSTER} start"
    sudo pg_ctlcluster "${PG_VERSION}" "${PG_CLUSTER}" start || true

  elif command -v pg_ctl &> /dev/null; then
    # Bare pg_ctl (e.g. Homebrew or manual install)
    PGDATA=${PGDATA:-/var/lib/postgresql/data}
    pg_ctl -D "$PGDATA" start || true

  elif command -v service &> /dev/null; then
    sudo service postgresql start || true

  elif command -v systemctl &> /dev/null; then
    sudo systemctl start postgresql || true
  fi

  # Wait up to 10 seconds
  for i in $(seq 1 10); do
    pg_isready -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" 2>/dev/null && break
    echo "    Waiting for PostgreSQL... ($i/10)"
    sleep 1
  done

  pg_isready -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" 2>/dev/null
  if [ $? -ne 0 ]; then
    echo "[✗] PostgreSQL still not reachable. Check your installation."
    echo "    Try: sudo service postgresql start"
    echo "    Or:  sudo systemctl start postgresql"
    exit 1
  fi
fi

echo "[✓] PostgreSQL is running"

# -----------------------------------------------
# 3. Drop and recreate the database
# -----------------------------------------------
echo ""
echo "--- Recreating database '${POSTGRES_DB}' ---"

PGPASSWORD="${POSTGRES_PASSWORD}" dropdb \
  --host="${POSTGRES_HOST}" \
  --port="${POSTGRES_PORT}" \
  --username="${POSTGRES_USER}" \
  --if-exists \
  "${POSTGRES_DB}"
echo "[✓] Dropped (if existed)"

PGPASSWORD="${POSTGRES_PASSWORD}" createdb \
  --host="${POSTGRES_HOST}" \
  --port="${POSTGRES_PORT}" \
  --username="${POSTGRES_USER}" \
  "${POSTGRES_DB}"
echo "[✓] Created '${POSTGRES_DB}'"

# -----------------------------------------------
# 4. Clear stale Alembic revision state
#    (the old revision IDs like 'add_failed_otp_attempts_20260318'
#     no longer exist — we wipe the DB so this is moot, but
#     also clear alembic's own heads cache just in case)
# -----------------------------------------------
echo ""
echo "--- Clearing Alembic state ---"
find . -name "__pycache__" -path "*/alembic/*" -exec rm -rf {} + 2>/dev/null || true
echo "[✓] Alembic cache cleared"

# -----------------------------------------------
# 5. Verify only ONE migration file exists
# -----------------------------------------------
echo ""
echo "--- Checking migration files ---"
MIGRATION_COUNT=$(find alembic/versions -name "*.py" -not -name "__init__.py" | wc -l)

if [ "$MIGRATION_COUNT" -ne 1 ]; then
  echo "[!] Expected 1 migration file, found ${MIGRATION_COUNT}:"
  find alembic/versions -name "*.py" -not -name "__init__.py"
  echo ""
  echo "    Delete all files except 20250223_0001_initial_migration.py and re-run."
  exit 1
fi

MIGRATION_FILE=$(find alembic/versions -name "*.py" -not -name "__init__.py")
echo "[✓] Single migration: ${MIGRATION_FILE}"

# Check down_revision is None
if ! grep -q "down_revision = None" "$MIGRATION_FILE"; then
  echo "[✗] Migration is not a base migration (down_revision is not None)"
  echo "    Check: ${MIGRATION_FILE}"
  exit 1
fi
echo "[✓] down_revision = None confirmed"

# -----------------------------------------------
# 6. Run migration
# -----------------------------------------------
echo ""
echo "--- Running alembic upgrade head ---"
alembic upgrade head

echo ""
echo "========================================"
echo "  Done! Schema applied successfully."
echo "========================================"
echo ""
echo "  Database: ${POSTGRES_DB}"
echo "  Tables created:"
PGPASSWORD="${POSTGRES_PASSWORD}" psql \
  --host="${POSTGRES_HOST}" \
  --port="${POSTGRES_PORT}" \
  --username="${POSTGRES_USER}" \
  --dbname="${POSTGRES_DB}" \
  --tuples-only \
  --command="SELECT '  - ' || tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;"
echo ""
