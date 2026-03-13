#!/bin/bash
pip install "flake8==5.0.4" "importlib-metadata<5.0"
flake8 --ignore "E,F,W" --select "E10,F82,F831,W191,W29,W601,W603,W604" esp/program/modules/handlers/studentclassregmodule.py esp/program/models/class_.py esp/program/modules/tests/issue_561_test.py
