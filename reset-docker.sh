#!/bin/bash

# PhishCatcher Docker Reset Script
# This script stops and removes all PhishCatcher containers and volumes

set -e

echo "🧹 Resetting PhishCatcher Docker environment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Get project name from docker-compose
PROJECT_NAME="phishcatcher"

echo "📦 Stopping and removing containers..."
docker-compose down 2>/dev/null || true

echo "🗑️  Removing PhishCatcher volumes..."
docker volume ls -q | grep -E "^${PROJECT_NAME}" | xargs -r docker volume rm 2>/dev/null || true
docker volume ls -q | grep -E "postgres_data|mongodb_data|redis_data|minio_data" | xargs -r docker volume rm 2>/dev/null || true

echo "🧽 Removing PhishCatcher networks..."
docker network ls -q | grep -E "${PROJECT_NAME}" | xargs -r docker network rm 2>/dev/null || true

echo "🗑️  Cleaning up orphaned containers..."
docker container prune -f 2>/dev/null || true

echo ""
echo "✅ Docker environment has been reset!"
echo ""
echo "To start fresh, run:"
echo "   ./quick-start.sh"
echo ""
echo "Or manually:"
echo "   docker-compose up -d"
echo "   cd phishcatcher-backend && alembic upgrade head"
echo "   python scripts/create_admin.py"
