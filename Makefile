# Everyday commands for Mile Marker API. GNU make.
#
# Every recipe line is one plain command, so the targets run the same under Linux, macOS,
# Git Bash, PowerShell and cmd.exe: no && chains, no shell conditionals, no VAR=value prefixes.
# The README lists the plain command behind each target, for anyone without make.

COMPOSE = docker compose
E2E_COMPOSE = docker compose -f docker-compose.yml -f docker-compose.e2e.yml
DEV_PORT = 8001
BASE_URL = http://127.0.0.1:8000
COLLECTION = docs/postman/milemarker.postman_collection.json

.PHONY: help up down logs ps dev migrate load shell test test-slow test-docker coverage \
	lint format typecheck audit check e2e-up e2e-down e2e live clean

help:
	@echo Mile Marker API. Run: make TARGET
	@echo help - List the targets
	@echo up - Build and start the stack in the background
	@echo down - Stop the stack, keeping the database volume
	@echo logs - Follow the API log
	@echo ps - Show the services and their states
	@echo dev - Start the database and Redis, then run the API from source with auto-reload on port $(DEV_PORT)
	@echo migrate - Apply migrations, from source
	@echo load - Load the fuel stations, from source
	@echo shell - Open a Django shell, from source
	@echo test - Run the test suite, from source
	@echo test-slow - Run the slow exactness test
	@echo test-docker - Run the test suite in a container
	@echo coverage - Run the suite with a coverage report in the terminal
	@echo lint - Ruff checks and format check
	@echo format - Ruff fixes and formatter
	@echo typecheck - Run mypy
	@echo audit - Check the locked dependencies for known faults
	@echo check - lint, typecheck and test
	@echo e2e-up - Start the end-to-end stack with the stand-in routing server, its cache empty
	@echo e2e-down - Stop the end-to-end stack
	@echo e2e - Run the whole Postman collection with Newman against the running end-to-end stack
	@echo live - Run scripts/live_check.py against the running stack. It calls the public routing server
	@echo clean - Stop everything and delete the volumes

up:
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f api

ps:
	$(COMPOSE) ps

dev:
	$(COMPOSE) up -d db redis
	uv run python manage.py runserver 127.0.0.1:$(DEV_PORT)

migrate:
	uv run python manage.py migrate

load:
	uv run python manage.py load_stations

shell:
	uv run python manage.py shell

test:
	uv run pytest

test-slow:
	uv run pytest -m slow

test-docker:
	$(COMPOSE) --profile test run --rm test

coverage:
	uv run pytest --cov

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

typecheck:
	uv run mypy

audit:
	uv run pip-audit

check: lint typecheck test

# The cache outlives the API, so a run that counts routing requests starts from an empty one:
# database 1, the end-to-end stack's own (docker-compose.e2e.yml).
e2e-up:
	$(E2E_COMPOSE) up --build -d
	$(E2E_COMPOSE) exec redis redis-cli -n 1 FLUSHDB

e2e-down:
	$(E2E_COMPOSE) down

e2e:
	npx --yes newman@6.2.3 run $(COLLECTION) --env-var base_url=$(BASE_URL) --timeout-request 60000

live:
	uv run python scripts/live_check.py --base-url $(BASE_URL)

clean:
	$(E2E_COMPOSE) down -v --remove-orphans
