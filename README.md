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


## Looking to contribute?

[Check out our wiki for details](https://github.com/learning-unlimited/ESP-Website/wiki#i-want-to-get-involved). We also have a strict [code of conduct](https://github.com/learning-unlimited/ESP-Website?tab=coc-ov-file).
