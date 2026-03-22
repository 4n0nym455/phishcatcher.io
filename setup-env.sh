#!/bin/bash

# PhishCatcher Environment Setup Script
# This script helps set up the .env file from the example

set -e

echo "🚀 PhishCatcher Environment Setup"
echo "================================="

# Check if .env exists
if [ -f .env ]; then
    echo "⚠️  .env file already exists!"
    echo "Do you want to overwrite it? (y/N)"
    read -r response
    if [[ ! $response =~ ^[Yy]$ ]]; then
        echo "❌ Setup cancelled."
        exit 1
    fi
fi

# Copy from example
if [ -f .env ]; then
    echo "✅ .env file already exists"
    echo "Current configuration:"
    echo ""
    cat .env
    echo ""
    echo "Do you want to overwrite it with the template? (y/N)"
    read -r response
    if [[ $response =~ ^[Yy]$ ]]; then
        cp env-template .env
        echo "✅ Updated .env file from env-template"
    fi
else
    cp env-template .env
    echo "✅ Created .env file from env-template"
fi

echo ""
echo "📝 Please edit the .env file with your configuration:"
echo ""
echo "Required changes:"
echo "• POSTGRES_PASSWORD - Set a secure password for PostgreSQL"
echo "• MONGO_PASSWORD - Set a secure password for MongoDB"
echo "• REDIS_PASSWORD - Set a secure password for Redis"
echo "• MINIO_PASSWORD - Set a secure password for MinIO"
echo "• SECRET_KEY - Generate a secure secret key"
echo "• JWT_SECRET_KEY - Generate a secure JWT secret key"
echo "• JWT_REFRESH_SECRET_KEY - Generate a secure JWT refresh secret key"
echo ""
echo "Optional but recommended:"
echo "• GOOGLE_CLIENT_ID & GOOGLE_CLIENT_SECRET - For Gmail integration"
echo "• SENDGRID_API_KEY - For email notifications"
echo "• VIRUSTOTAL_API_KEY - For threat intelligence"
echo ""
echo "🔧 Quick setup commands:"
echo "   # Generate secure secrets:"
echo "   openssl rand -hex 32  # For SECRET_KEY"
echo "   openssl rand -hex 32  # For JWT_SECRET_KEY"
echo "   openssl rand -hex 32  # For JWT_REFRESH_SECRET_KEY"
echo ""
echo "   # Edit the .env file:"
echo "   nano .env"
echo ""
echo "📚 After configuring .env, run:"
echo "   ./quick-start.sh"
echo ""
echo "🎉 Setup complete! Don't forget to edit .env with your actual values."
