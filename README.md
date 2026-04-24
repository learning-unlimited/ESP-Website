[![License](https://img.shields.io/github/license/learning-unlimited/ESP-Website)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-Django%20app-3776AB?logo=python&logoColor=white)](#development)
[![Docker](https://img.shields.io/badge/Docker-dev%20setup-2496ED?logo=docker&logoColor=white)](#quick-start)

# ESP Website

ESP Website is the platform that Learning Unlimited chapters use to run short-term educational programs. It helps organizers manage program logistics, admissions, classes, scheduling, and the chapter website from one codebase.

It is maintained by members and alumni of the Splash community and Learning Unlimited.

## Table of Contents
- [What this project is for](#what-this-project-is-for)
- [Quick start](#quick-start)
- [Common development tasks](#common-development-tasks)
- [Project layout](#project-layout)
- [Documentation](#documentation)
- [Contributing](#contributing)

## What this project is for

Use ESP Website when you need to run programs such as Splash-style events and want a self-hosted system for:

- chapter and program administration
- student and teacher flows
- registration and scheduling
- theme and content customization
- ongoing site operations

## Quick start

The fastest local setup uses Docker.

### Prerequisites
- Docker Desktop, or Docker Engine + Docker Compose plugin
- Git

### Run locally
```bash
git clone https://github.com/learning-unlimited/ESP-Website.git devsite
cd devsite
docker compose up --build
```

Then open <http://localhost:8000>.

To create an admin user:
```bash
docker compose exec web python esp/manage.py createsuperuser
```

## Common development tasks

### Run tests
```bash
docker compose exec web python esp/manage.py test
```

### Open a Django shell
```bash
docker compose exec web python esp/manage.py shell_plus
```

### Seed demo data
```bash
docker compose exec web python esp/manage.py seed_dummy_data
```

### Rebuild after dependency changes
```bash
docker compose down
docker compose up --build
```

## Project layout

```text
esp/          Main Django application and project code
docs/         Admin and developer documentation
docker/       Docker-related configuration
Dockerfile    Container image for local development
```

## Documentation

- Admin and developer docs: [`docs/`](./docs)
- Docker setup: [`docs/dev/docker.rst`](./docs/dev/docker.rst)
- Contributing guide: [`docs/dev/contributing.rst`](./docs/dev/contributing.rst)
- Customization guide: [`docs/customizing.rst`](./docs/customizing.rst)
- Learning Unlimited wiki: <https://wiki.learningu.org>

## Contributing

Contributions are welcome. A typical flow is:

1. Fork the repository
2. Create a feature branch
3. Make and test your changes
4. Open a pull request

If you are new to the codebase, starting with the Docker workflow and reading the docs in `docs/dev/` is the easiest path.

## License

This project is released under the license in [`LICENSE`](./LICENSE).
