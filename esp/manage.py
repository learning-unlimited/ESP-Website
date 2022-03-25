#!/usr/bin/env python
import os
import sys

# Check if a virtualenv has been installed and activated from elsewhere.
# This happens when using the Travis testing environment, which uses its
# own virtualenv install.
# If this has happened, then the VIRTUAL_ENV environment variable should be
# defined.
# If the variable isn't defined, then activate our own virtualenv.
# Alternatively, if we're using the Github Actions testing environment,
# then the GITHUB_ACTIONS environment variable should be set to true.
if os.environ.get('VIRTUAL_ENV') is None and not os.environ.get('GITHUB_ACTIONS'):
    project = os.path.dirname(os.path.realpath(__file__))
    root = os.path.dirname(project)
    activate_this = os.path.join(root, 'env', 'bin', 'activate_this.py')
    execfile(activate_this, dict(__file__=activate_this))

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "esp.settings")
    os.environ.setdefault("DJANGO_IS_IN_SCRIPT",
                          # A bit ugly, but we want runserver/runserver_plus
                          # not to act like scripts.
                          str(not any('runserver' in arg for arg in sys.argv)))

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
