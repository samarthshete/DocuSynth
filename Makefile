.PHONY: up down restart logs health test benchmark smoke streamlit clean-benchmark

up:
	docker compose up -d postgres redis python-rag backend prometheus grafana

down:
	docker compose down --remove-orphans

restart:
	docker compose down --remove-orphans
	docker compose up -d postgres redis python-rag backend prometheus grafana

logs:
	docker compose logs -f backend python-rag

health:
	curl -s http://localhost:8080/health | python3 -m json.tool
	curl -s http://localhost:8001/health | python3 -m json.tool
	curl -s "http://localhost:9091/api/v1/query?query=up" | python3 -m json.tool

test:
	docker compose --profile test run --rm test

smoke:
	python3 scripts/smoke_ollama.py

benchmark:
	rm -f tests/benchmark_results.json tests/benchmark_results_raw.json
	python3 tests/bench_semantic_cache.py --delay-seconds 0.0
	cat tests/benchmark_results.json

streamlit:
	streamlit run streamlit/app.py

clean-benchmark:
	mkdir -p docs/benchmarks
	cp tests/benchmark_results.json docs/benchmarks/benchmark_ollama_fast_final.json
	cp tests/benchmark_results_raw.json docs/benchmarks/benchmark_ollama_fast_raw_final.json
