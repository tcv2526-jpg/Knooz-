#!/bin/bash
set -e

echo ""
echo "🚀 Starting Knooz ERP..."
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
  echo "❌ Docker not found. Install Docker Desktop from https://docker.com"
  exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
  echo "❌ Docker Compose not found."
  exit 1
fi

COMPOSE="docker compose"
command -v docker-compose &> /dev/null && COMPOSE="docker-compose"

echo "📦 Building and starting containers..."
$COMPOSE up -d --build

echo ""
echo "⏳ Waiting for database..."
sleep 8

echo ""
echo "🌱 Running seed (creating admin user)..."
$COMPOSE exec backend python seed.py

echo ""
echo "═══════════════════════════════════════════"
echo "  ✅ Knooz ERP is running!"
echo ""
echo "  🌐 Frontend:  http://localhost:3000"
echo "  🔌 API:       http://localhost:8000"
echo "  📖 API Docs:  http://localhost:8000/api/docs"
echo "  🗄️  Via Nginx: http://localhost:80"
echo ""
echo "  Login: admin@knooz.com / admin123"
echo "═══════════════════════════════════════════"
echo ""
