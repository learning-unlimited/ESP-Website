.PHONY: help build up down migrate shell superuser test lint clean

# help: List available commands with short descriptions.
help:
	@echo "Available commands:"
	@echo "  build      - Run docker compose build"
	@echo "  up         - Run docker compose up -d"
	@echo "  down       - Run docker compose down"
	@echo "  migrate    - Run Django migrations inside the web container"
	@echo "  shell      - Open Django shell inside the web container"
	@echo "  superuser  - Create Django superuser inside the web container"
	@echo "  test       - Run tests inside the web container"
	@echo "  coverage   - Run tests with coverage reporting"
	@echo "  lint       - Run linting checks inside the web container"
	@echo "  static     - Collect static files"
	@echo "  db-reset   - Reset the database (flush)"
	@echo "  clean      - Stop containers and remove volumes"

# build: Run docker compose build.
build:
	docker compose build

# up: Run docker compose up -d.
up:
	docker compose up -d

# down: Run docker compose down.
down:
	docker compose down

# migrate: Run Django migrations inside the web container.
migrate:
	docker compose exec web python esp/manage.py migrate

# shell: Open Django shell inside the web container.
shell:
	docker compose exec web python esp/manage.py shell

# superuser: Create Django superuser inside the web container.
superuser:
	docker compose exec web python esp/manage.py createsuperuser

# test: Run tests (use existing test command in the project).
test:
	docker compose exec web python esp/manage.py test

# lint: Run existing linting tool used in the project (detect from repo).
lint:
	docker compose exec web ./deploy/lint

# static: Collect static files.
static:
	docker compose exec web python esp/manage.py collectstatic --noinput

# db-reset: Reset the database (flush).
db-reset:
	docker compose exec web python esp/manage.py flush --noinput

# coverage: Run tests with coverage reporting.
coverage:
	docker compose exec web coverage run esp/manage.py test
	docker compose exec web coverage report
	docker compose exec web coverage html

# clean: Stop containers and remove volumes.
clean:
	docker compose down -v
