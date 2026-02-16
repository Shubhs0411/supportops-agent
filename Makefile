.PHONY: setup lint test run demo evals clean docker-up docker-down

setup:
	pip install -e ".[dev]"
	cp .env.example .env || true

lint:
	ruff check supportops_agent tests
	ruff format --check supportops_agent tests

test:
	pytest -q

run:
	uvicorn supportops_agent.api.main:app --reload --host 0.0.0.0 --port 8000

demo:
	python -m supportops_agent.cli triage --ticket evals/fixtures/ticket_01.json

evals:
	python -m supportops_agent.evals.run --suite evals/suite.yaml

docker-up:
	docker compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	@echo "API: http://localhost:8000"
	@echo "Jaeger UI: http://localhost:16686"
	@echo "Docs: http://localhost:8000/docs"

docker-down:
	docker compose down -v

clean:
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache
