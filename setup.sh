#!/bin/bash

# PhishCatcher Quick Start Script
# Backend & Frontend run locally, Services run in Docker

set -e

echo "🚀 Starting PhishCatcher Development Environment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install it first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p phishcatcher-backend/models
mkdir -p phishcatcher-backend/uploads
mkdir -p phishcatcher-backend/logs
mkdir -p phishcatcher-backend/nginx/ssl

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose down 2>/dev/null || true

# Start infrastructure services in Docker (no backend/frontend)
echo "🐳 Starting Docker services (PostgreSQL, MongoDB, Redis, MinIO)..."
docker-compose up -d postgres mongodb redis minio minio-init

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 20

# Check if services are healthy
echo "🔍 Checking Docker service health..."
for service in postgres mongodb redis minio; do
    if docker ps | grep -q "phishcatcher-$service"; then
        echo "✅ $service is running"
    else
        echo "⚠️  $service may not be running"
    fi
done

# Setup backend environment (local)
echo "🔧 Setting up backend environment..."

cd phishcatcher-backend

# Check if .env exists in backend
if [ ! -f .env ]; then
    if [ -f ../.env ]; then
        cp ../.env .env
        echo "✅ Copied .env from project root"
    else
        echo "⚠️  No .env file found. Please create one:"
        echo "   cp env-template .env && nano .env"
        echo "   Then run this script again."
        exit 1
    fi
else
    echo "✅ .env file found"
fi

# Activate virtual environment
if [ ! -d ".venv" ]; then
    echo "🐍 Creating virtual environment..."
    python3 -m venv .venv
fi

echo "📦 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt 2>/dev/null || true

# Run database migrations
echo "🗃️  Running database migrations..."
alembic upgrade head

# Create admin user (will prompt for input)
echo "👤 Creating admin user..."
echo "   You can skip this step if admin already exists."
PYTHONPATH=. python scripts/create_admin.py || echo "Admin creation skipped or failed"

# Start backend server (local)
echo "🚀 Starting backend server locally..."
source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start celery worker (local)
echo "🚀 Starting Celery worker locally..."
celery -A app.tasks.celery_app worker --loglevel=info &
CELERY_PID=$!

# Setup frontend (local)
echo "🎨 Setting up frontend..."
cd ../phishcatcher-frontend/app

# Install Node.js dependencies
if [ ! -d "node_modules" ]; then
    echo "📦 Installing Node.js dependencies..."
    npm install
fi

# Create frontend environment file
if [ ! -f ".env.local" ]; then
    echo "📝 Creating frontend environment file..."
    cat > .env.local << EOF
REACT_APP_API_URL=http://localhost:8000/api/v1
REACT_APP_WS_URL=ws://localhost:8000/ws
EOF
fi

# Start frontend server (local)
echo "🚀 Starting frontend server locally..."
npm run dev &
FRONTEND_PID=$!

# Wait for servers to start
echo "⏳ Waiting for servers to start..."
sleep 10

echo ""
echo "🎉 PhishCatcher is ready!"
echo ""
echo "📋 Services running:"
echo "   🔵 Docker (Infrastructure):"
echo "      • PostgreSQL: localhost:5432"
echo "      • MongoDB: localhost:27017"
echo "      • Redis: localhost:6379"
echo "      • MinIO Console: http://localhost:9001"
echo "      • MinIO API: http://localhost:9000"
echo ""
echo "   🟢 Local (Development):"
echo "      • Frontend: http://localhost:5173"
echo "      • Backend API: http://localhost:8000"
echo "      • API Docs: http://localhost:8000/docs"
echo "      • Celery Worker: celery -A app.tasks.celery_app worker --loglevel=info"
echo ""
echo "🔑 Default admin:"
echo "   • Email: (set during admin creation or check .env)"
echo "   • Password: (set during admin creation)"
echo ""
echo "🛑 To stop all services:"
echo "   • Docker: docker-compose down"
echo "   • Backend: kill $BACKEND_PID"
echo "   • Celery: kill $CELERY_PID"
echo "   • Frontend: kill $FRONTEND_PID"
