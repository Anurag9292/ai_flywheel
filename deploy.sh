#!/bin/bash
# AI Flywheel — Fly.io Deployment Script
# 
# Prerequisites:
#   1. Install flyctl: curl -L https://fly.io/install.sh | sh
#   2. Login: fly auth login
#   3. Create apps (first time only):
#      fly apps create ai-flywheel-api
#      fly apps create ai-flywheel-web
#   4. Create Postgres (first time only):
#      fly postgres create --name ai-flywheel-db --region sjc
#      fly postgres attach ai-flywheel-db --app ai-flywheel-api
#   5. Create Redis (first time only):
#      fly redis create --name ai-flywheel-redis --region sjc
#   6. Set secrets:
#      fly secrets set OPENAI_API_KEY=sk-... --app ai-flywheel-api
#      fly secrets set JWT_SECRET_KEY=$(openssl rand -hex 32) --app ai-flywheel-api
#      fly secrets set TEMPORAL_HOST=<your-temporal-cloud-address> --app ai-flywheel-api

set -e

echo "🚀 Deploying AI Flywheel to Fly.io..."

# Deploy backend
echo ""
echo "📦 Deploying Backend API..."
fly deploy --app ai-flywheel-api

# Run migrations
echo ""
echo "🗄️  Running database migrations..."
fly ssh console --app ai-flywheel-api -C "alembic upgrade head"

# Deploy frontend
echo ""
echo "🎨 Deploying Frontend..."
cd frontend
fly deploy --app ai-flywheel-web
cd ..

echo ""
echo "✅ Deployment complete!"
echo ""
echo "   Backend:  https://ai-flywheel-api.fly.dev"
echo "   Frontend: https://ai-flywheel-web.fly.dev"
echo ""
echo "   Health:   https://ai-flywheel-api.fly.dev/health"
