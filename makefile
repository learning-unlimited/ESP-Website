.PHONY: help setup test lint run migrate collect-static db-reset db-seed clean docker-up docker-down docker-build docker-logs docker-shell

help:
	@echo "ESP-Website Development Commands"
	@echo "=================================="
	@echo "make setup           - Install dependencies and configure development"
	@echo "make test            - Run tests with coverage"
	@echo "make lint            - Run code linting (flake8)"
	@echo "make migrate         - Run Django migrations"
	@echo "make collect-static  - Collect static files"
	@echo "make db-reset        - Drop and recreate test database"
	@echo "make run             - Start Django development server (local)"
	@echo ""
	@echo "Docker Compose Commands:"
	@echo "make docker-up       - Start all services (db, memcached, web)"
	@echo "make docker-down     - Stop all services"
	@echo "make docker-build    - Build web service image"
	@echo "make docker-logs     - View service logs"
	@echo "make docker-shell    - Open bash shell in web container"
	@echo "make docker-clean    - Remove containers and volumes"

# Development Setup
setup:
	@echo "Installing dependencies..."
	pip install -r esp/requirements.txt
	pip install flake8 coverage
	cd esp && ./manage.py migrate

# Testing
test:
	cd esp && ./manage.py collectstatic --noinput -v 0
	cd esp && coverage run --source=. ./manage.py test
	coverage xml

test-ci: db-reset test

# Linting
lint:
	flake8 esp/

# Database
db-reset:
	psql -c "DROP DATABASE IF EXISTS test_django;" -U postgres || true
	psql -c "DROP ROLE IF EXISTS testuser;" -U postgres || true
	psql -c "CREATE ROLE testuser PASSWORD 'testpassword' LOGIN CREATEDB;" -U postgres
	psql -c "CREATE DATABASE test_django OWNER testuser;" -U postgres

# Django management
migrate:
	cd esp && ./manage.py migrate

collect-static:
	cd esp && ./manage.py collectstatic --noinput -v 0

run:
	cd esp && ./manage.py runserver_plus 0.0.0.0:8000

# Docker Compose
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-build:
	docker-compose build

docker-logs:
	docker-compose logs -f

docker-shell:
	docker-compose exec web bash

docker-clean:
	docker-compose down -v
	docker system prune -f

# Docker Compose with Django commands
docker-migrate: docker-up
	docker-compose exec web python manage.py migrate

docker-collect-static: docker-up
	docker-compose exec web python manage.py collectstatic --noinput -v 0

docker-test: docker-up
	docker-compose exec web python manage.py test


# Cleanup
clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	rm -rf htmlcov/ .coverage coverage.xml