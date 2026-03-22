#!/bin/bash

# PhishCatcher Quick Start Script
# This script sets up the development environment

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

# Start databases and services
echo "🗄️  Starting databases and services..."
docker-compose -f docker-compose.simple.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are healthy
echo "🔍 Checking service health..."
for service in postgres mongodb redis minio; do
    if docker-compose -f docker-compose.simple.yml ps | grep -q "$service.*Up"; then
        echo "✅ $service is running"
    else
        echo "❌ $service failed to start"
        docker-compose -f docker-compose.simple.yml logs $service
        exit 1
    fi
done

# Setup backend environment
echo "🔧 Setting up backend environment..."
cd phishcatcher-backend

# Check if .env exists, if not create from example
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env-template .env
    echo "⚠️  Please edit phishcatcher-backend/.env with your configuration"
else
    echo "✅ .env file found"
    echo "📋 Current environment configuration:"
    echo "   • Frontend URL: $(grep FRONTEND_URL .env | cut -d'=' -f2)"
    echo "   • Backend Database: $(grep DATABASE_URL .env | cut -d'@' -f2 | cut -d':' -f1)"
    echo "   • MongoDB: $(grep MONGODB_URL .env | cut -d'@' -f2 | cut -d':' -f1)"
    echo "   • Redis: $(grep REDIS_URL .env | cut -d'@' -f2 | cut -d':' -f1)"
    echo "   • MinIO: $(grep MINIO_ENDPOINT .env | cut -d'=' -f2)"
    echo "   • Gmail OAuth: Configured"
    echo "   • SendGrid: $(grep SENDGRID_API_KEY .env | cut -d'=' -f1)"
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
pip install -r requirements.txt

# Run database migrations
echo "🗃️  Running database migrations..."
alembic upgrade head

# Create admin user
echo "👤 Creating admin user..."
PYTHONPATH=. python scripts/create_admin.py

# Start backend server
echo "🚀 Starting backend server..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Setup frontend
echo "🎨 Setting up frontend..."
cd ../phishcatcher-frontend/app

# Install Node.js dependencies
if [ ! -d "node_modules" ]; then
    echo "📦 Installing Node.js dependencies..."
    npm install
fi

# Create frontend environment file
if [ ! -f .env.local ]; then
    echo "📝 Creating frontend environment file..."
    cat > .env.local << EOF
REACT_APP_API_URL=http://localhost:8000/api/v1
REACT_APP_WS_URL=ws://localhost:8000/ws
EOF
fi

# Start frontend server
echo "🚀 Starting frontend server..."
npm run dev &
FRONTEND_PID=$!

# Wait for servers to start
echo "⏳ Waiting for servers to start..."
sleep 15

# Check if servers are running
echo "🔍 Checking server status..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Backend server is running on http://localhost:8000"
else
    echo "❌ Backend server failed to start"
fi

if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Frontend server is running on http://localhost:3000"
else
    echo "❌ Frontend server failed to start"
fi

echo ""
echo "🎉 PhishCatcher development environment is ready!"
echo ""
echo "📋 Services running:"
echo "   • Frontend: http://localhost:5137"
echo "   • Backend API: http://localhost:8000"
echo "   • API Docs: http://localhost:8000/docs"
echo "   • PostgreSQL: postgres:5432"
echo "   • MongoDB: mongodb:27017"
echo "   • Redis: redis:6379"
echo "   • MinIO Console: http://localhost:9001"
echo "   • MinIO API: http://localhost:9000"
echo "   • Flower (Celery): http://localhost:5555"
echo ""
echo "🛑 To stop all services, run:"
echo "   docker-compose -f docker-compose.simple.yml down"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "📚 For more information, see the documentation in the docs/ directory."
