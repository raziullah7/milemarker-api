# The few commands worth remembering. `make help` lists them.
#
# Every recipe line is one plain command, so they run the same under Linux, macOS, Git Bash
# and PowerShell. Nothing here is needed: README.md and docs/development.md give the plain
# commands.

COMPOSE = docker compose
OFFLINE = docker compose -f docker-compose.yml -f docker-compose.e2e.yml

.PHONY: help up down logs test lint dev offline postman clean

help:
	@echo make up       Start everything. The API answers on http://127.0.0.1:8000
	@echo make down     Stop everything
	@echo make logs     Follow the API log
	@echo make test     Run the tests, in a container
	@echo make lint     Run the linter, the format check and the type check
	@echo make dev      Run the API from source with auto-reload, on port 8001
	@echo make offline  Start everything on recorded roads, with no call to the public routing server
	@echo make postman  Run the Postman collection against the running API
	@echo make clean    Stop everything and delete the database

up:
	$(COMPOSE) up --build -d

down:
	$(OFFLINE) down --remove-orphans

logs:
	$(COMPOSE) logs -f api

test:
	$(COMPOSE) --profile test run --rm test

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy

dev:
	$(COMPOSE) up -d db redis
	uv run python manage.py runserver 127.0.0.1:8001

# The cache outlives the API, so the recorded roads get a Redis database of their own, emptied
# at each start (docker-compose.e2e.yml).
offline:
	$(OFFLINE) up --build -d
	$(OFFLINE) exec redis redis-cli -n 1 FLUSHDB

postman:
	npx --yes newman@6.2.3 run docs/postman/milemarker.postman_collection.json --env-var base_url=http://127.0.0.1:8000 --timeout-request 60000

clean:
	$(OFFLINE) down -v --remove-orphans
