#!/bin/bash
# AI Flywheel — Full Stack Deployment
#
# Deploys everything with Docker Compose:
#   - PostgreSQL 16 + pgvector
#   - Redis 7
#   - Temporal + Temporal UI
#   - API (FastAPI)
#   - Worker (Temporal activities)
#   - Frontend (Next.js)
#
# Usage:
#   # Set your OpenAI key
#   export OPENAI_API_KEY=sk-...
#
#   # Deploy everything
#   ./deploy.sh
#
#   # Or deploy to a remote server:
#   ssh your-server "cd /app && git pull && ./deploy.sh"
#
# Requirements:
#   - Docker & Docker Compose v2
#   - At least 2GB RAM

set -e

echo "🚀 AI Flywheel — Full Stack Deploy"
echo ""

# Check requirements
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Install: https://docs.docker.com/get-docker/"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not set. LLM features won't work."
    echo "   Set it with: export OPENAI_API_KEY=sk-..."
    echo ""
fi

# Generate JWT secret if not set
export JWT_SECRET_KEY=${JWT_SECRET_KEY:-$(openssl rand -hex 32)}

echo "📦 Building containers..."
docker compose build

echo ""
echo "🗄️  Starting infrastructure (Postgres, Redis, Temporal)..."
docker compose up -d postgres redis temporal temporal-ui
sleep 10

echo ""
echo "🔄 Running migrations..."
docker compose run --rm migrate

echo ""
echo "🚀 Starting application..."
docker compose up -d api worker frontend

echo ""
echo "✅ Deployment complete!"
echo ""
echo "   Frontend:    http://localhost:3000"
echo "   API:         http://localhost:8000"
echo "   API Docs:    http://localhost:8000/docs"
echo "   Temporal UI: http://localhost:8080"
echo "   Health:      http://localhost:8000/health"
echo ""
echo "   Logs:        docker compose logs -f"
echo "   Stop:        docker compose down"
echo "   Destroy:     docker compose down -v"
