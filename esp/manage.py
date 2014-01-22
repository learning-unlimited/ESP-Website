#!/usr/bin/env python
import os
import sys

# activate virtualenv
project = os.path.dirname(os.path.realpath(__file__))
root = os.path.dirname(project)
activate_this = os.path.join(root, 'env', 'bin', 'activate_this.py')
try:
    execfile(activate_this, dict(__file__=activate_this))
except IOError, e:
    # Check if a virtualenv has been installed and activated from elsewhere.
    # This happens when using the Travis testing environment, which uses its
    # own virtualenv install.
    # If this has happened, then the VIRTUAL_ENV environment variable should be
    # defined, and we can ignore the IOError.
    # If the variable isn't defined, then we really should be using our own
    # virtualenv, so we re-raise the error.
    if os.environ.get('VIRTUAL_ENV') is None:
        raise e

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "esp.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
