#!/usr/bin/env bash
set -euo pipefail

# ColorForge AI — Bootstrap script
# Run this once after cloning the repo to set up the development environment.

echo "=== ColorForge AI Bootstrap ==="

# Check prerequisites
command -v node >/dev/null 2>&1 || { echo "Node.js required (>=20.10)"; exit 1; }
command -v pnpm >/dev/null 2>&1 || { echo "pnpm required (9.12+)"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker required"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Python 3.12+ required"; exit 1; }

echo "1/6 — Copying environment file..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo "  Created .env from .env.example"
else
  echo "  .env already exists, skipping"
fi

echo "2/6 — Installing Node.js dependencies..."
pnpm install

echo "3/6 — Installing Python dependencies..."
if command -v uv >/dev/null 2>&1; then
  uv sync
else
  echo "  uv not found, using pip..."
  pip install -e apps/agents
fi

echo "4/6 — Starting infrastructure (Postgres, Qdrant, Redis)..."
make infra-up

echo "5/6 — Running database migrations..."
pnpm db:push

echo "6/6 — Seeding database..."
pnpm db:seed

echo ""
echo "=== Bootstrap complete! ==="
echo "Run 'make check' to verify everything works."
echo "Run 'make help' to see all available commands."
