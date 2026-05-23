#!/bin/bash
# OpenEngage Setup Script
# Run: chmod +x setup.sh && ./setup.sh

set -e
echo "🚀 OpenEngage — LLM-Powered Marketing Automation Setup"
echo "======================================================="

# Pull models into Ollama
echo "📥 Pulling LLM model (Qwen3:8b) into Ollama..."
docker compose exec ollama ollama pull qwen3:8b
docker compose exec ollama ollama pull nomic-embed-text

# Initialize databases
echo "🗄️  Initializing databases..."
docker compose exec ai_gateway alembic upgrade head

# Setup Superset
echo "📊 Setting up Apache Superset..."
docker compose exec superset superset db upgrade
docker compose exec superset superset init
docker compose exec superset superset fab create-admin \
    --username admin --firstname Admin --lastname OpenEngage \
    --email admin@openengage.local --password admin123

# Setup MinIO buckets
echo "🗂️  Creating MinIO buckets..."
docker compose exec minio mc alias set local http://localhost:9000 openengage openengage123
docker compose exec minio mc mb local/email-assets
docker compose exec minio mc mb local/landing-pages
docker compose exec minio mc mb local/contact-imports

echo ""
echo "✅ OpenEngage is ready!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🌐 Frontend:      http://localhost:3000"
echo "⚙️  Mautic Core:   http://localhost:8080"
echo "🤖 AI Gateway:    http://localhost:8000"
echo "📊 Superset:      http://localhost:8088  (admin/admin123)"
echo "💬 Chatwoot:      http://localhost:3001"
echo "📧 Postal:        http://localhost:5000"
echo "🗂️  MinIO:         http://localhost:9001  (openengage/openengage123)"
echo "🔗 ChromaDB:      http://localhost:8001"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📖 API Docs:      http://localhost:8000/docs"
echo "🔌 WebSocket:     ws://localhost:8000/ws/copilot/{session_id}"
