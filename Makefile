.PHONY: setup db-up migrate seed dev check test test-browser db-down
setup:
	python3.12 scripts/setup.py
db-up:
	docker compose up -d --wait db
migrate:
	uv run --locked python -m living_memory.cli migrate
seed:
	uv run --locked python -m living_memory.cli seed
	uv run --locked python -m living_memory.cli seed --fixture orchid-accord
dev:
	uv run --locked uvicorn living_memory.app:create_app --factory --host 127.0.0.1 --port 8000 --reload --no-access-log
check:
	uv run --locked ruff check .
	uv run --locked mypy
test:
	uv run --locked pytest --ignore=tests/browser
test-browser:
	uv run --locked pytest tests/browser
db-down:
	docker compose down
