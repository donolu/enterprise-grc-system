PYTHON ?= python3.12
VENV ?= .venv312

.PHONY: up down logs migrate createsuper shell test bootstrap setup-hooks

up:
	docker compose up -d --build
down:
	docker compose down
logs:
	docker compose logs -f web worker beat
migrate:
	docker compose exec web python manage.py migrate
createsuper:
	docker compose exec web python manage.py createsuperuser
shell:
	docker compose exec web python manage.py shell_plus || docker compose exec web python manage.py shell
test:
	docker compose exec web pytest -q
bootstrap:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/python -m pip install --upgrade pip
	$(VENV)/bin/python -m pip install -r requirements-dev.txt
	(cd frontend && npm ci --legacy-peer-deps)
	$(MAKE) setup-hooks

setup-hooks:
	$(VENV)/bin/pre-commit install --install-hooks --hook-type pre-commit --hook-type pre-push
