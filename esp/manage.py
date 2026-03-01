#!/usr/bin/env python
import os
import sys
from io import open

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "esp.settings")
    os.environ.setdefault("DJANGO_IS_IN_SCRIPT",
                          # A bit ugly, but we want runserver/runserver_plus
                          # not to act like scripts.
                          str(not any('runserver' in arg for arg in sys.argv)))

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
