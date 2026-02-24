[![Lint and Unit Tests](https://github.com/learning-unlimited/ESP-Website/actions/workflows/tests.yml/badge.svg)](https://github.com/learning-unlimited/ESP-Website/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/learning-unlimited/ESP-Website/branch/main/graph/badge.svg?token=eY0C5a1Lju)](https://codecov.io/gh/learning-unlimited/ESP-Website)

# ESP Website

This repository contains a website to help manage the logistics of preparing for and running large, short-term educational programs. It is written and maintained by members and alums of the interscholastic Splash community and [Learning Unlimited](https://learningu.org). Documentation for [program administrators](/docs/admin) and [developers](/docs/dev) is in the [`docs`](/docs) directory, including [dev setup documentation](/docs/dev/docker.rst) and [instructions for contributors](/docs/dev/contributing.rst). Additional documentation for chapters of Learning Unlimited is on the [LU Wiki](https://wiki.learningu.org).

## Quick Start (Docker)

The fastest way to get a local development server running:

```bash
git clone https://github.com/learning-unlimited/ESP-Website.git devsite
cd devsite
docker compose up --build
```

Then visit http://localhost:8000. See the [Docker setup guide](/docs/dev/docker.rst) for full details.

## Testing

This project uses Django's built-in test framework. All tests are located in `esp/esp/tests/` with filenames that indicate the source module they cover (e.g., `test_accounting_models.py` tests `esp/esp/accounting/models.py`).

### Test Suite Overview

| Test File | Source Module |
|-----------|--------------|
| `test_accounting_models.py` | `accounting/models.py` |
| `test_accounting_controllers.py` | `accounting/controllers.py` |
| `test_application_models.py` | `application/models.py` |
| `test_cal_models.py` | `cal/models.py` |
| `test_classreg_controller.py` | `program/controllers/classreg.py` |
| `test_context_processors.py` | `context_processors.py` |
| `test_db_fields.py` | `db/fields.py` |
| `test_dbmail_cronmail.py` | `dbmail/cronmail.py` |
| `test_dbmail_models.py` | `dbmail/models.py` |
| `test_formstack_objects.py` | `formstack/objects.py` |
| `test_middleware.py` | `middleware/espauthmiddleware.py` |
| `test_middleware_error.py` | `middleware/esperrormiddleware.py` |
| `test_miniblog_models.py` | `miniblog/models.py` |
| `test_program_controllers.py` | `program/controllers/confirmation.py` |
| `test_survey_models.py` | `survey/models.py` |
| `test_varnish.py` | `varnish/varnish.py` |

Additional existing tests in module directories: `customforms/tests.py`, `program/tests.py`, `users/tests.py`, `resources/tests.py`, `qsd/tests.py`, `qsdmedia/tests.py`, `tagdict/tests.py`, `themes/tests.py`, `utils/tests.py`, `web/tests.py`, and autoscheduler tests in `program/controllers/autoscheduler/`.

### Running Tests

**Using Docker (recommended):**
```bash
# Run all tests
docker exec -it esp-website-web-1 bash -c "cd /code/esp && python manage.py test --settings=esp.settings 2>&1"

# Run tests for a specific module
docker exec -it esp-website-web-1 bash -c "cd /code/esp && python manage.py test esp.tests.test_accounting_models --settings=esp.settings 2>&1"

# Run the central test suite only
docker exec -it esp-website-web-1 bash -c "cd /code/esp && python manage.py test esp.tests --settings=esp.settings 2>&1"
```

**Without Docker:**
```bash
cd esp
python manage.py test --settings=esp.settings
```

### ⚠️ PR Requirement

> **All test cases must pass before submitting a Pull Request.** If your changes break existing tests, fix them before requesting a review. If you add new functionality, add corresponding tests in `esp/esp/tests/` following the naming convention `test_<module>_<component>.py`.

## Looking to contribute?

[Check out our wiki for details](https://github.com/learning-unlimited/ESP-Website/wiki#i-want-to-get-involved). We also have a strict [code of conduct](https://github.com/learning-unlimited/ESP-Website?tab=coc-ov-file).
