.PHONY: help install infra-up infra-down db-migrate db-seed check test lint kill

help:
	@echo "ColorForge AI — Available commands:"
	@echo "  make install      Install all deps (pnpm + uv)"
	@echo "  make infra-up     Start Postgres+Qdrant+Redis"
	@echo "  make infra-down   Stop infra"
	@echo "  make db-migrate   Run Prisma migrations"
	@echo "  make db-seed      Seed initial data"
	@echo "  make check        Lint + typecheck + test (TS + Python)"
	@echo "  make test         Run all tests"
	@echo "  make kill         Emergency killswitch"

install:
	pnpm install
	uv sync

infra-up:
	docker compose -f infra/docker-compose.yml up -d
	@echo "Waiting for Postgres..."
	@until docker exec colorforge-postgres pg_isready -U colorforge >/dev/null 2>&1; do sleep 1; done
	@echo "✅ Infra up"

infra-down:
	docker compose -f infra/docker-compose.yml down

db-migrate:
	pnpm db:migrate

db-seed:
	pnpm db:seed

check:
	pnpm check

test:
	pnpm test

test-changed:
	pnpm vitest run --changed

lint:
	pnpm lint

kill:
	python scripts/kill.py
