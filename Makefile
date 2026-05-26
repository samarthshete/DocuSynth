SHELL := /bin/bash

.PHONY: up down ps logs test bench-mock bench-real health

up:
	docker compose up --build

down:
	docker compose down -v

ps:
	docker compose ps

logs:
	docker compose logs -f

test:
	docker compose --profile test run --rm test

bench-mock:
	python tests/bench_semantic_cache.py --mock-llm

bench-real:
	python tests/bench_semantic_cache.py

health:
	curl -fsS http://localhost:8080/health
	curl -fsS http://localhost:8080/metrics | grep docusynth
	curl -fsS http://localhost:8001/health
	docker compose exec redis redis-cli ping
	docker compose exec postgres psql -U docusynth -d docusynth -c "CREATE EXTENSION IF NOT EXISTS vector;"
	docker compose exec postgres psql -U docusynth -d docusynth -c "SELECT extname FROM pg_extension WHERE extname='vector';"
