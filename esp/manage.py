#!/usr/bin/env python

import os.path
project = os.path.dirname(os.path.realpath(__file__))
root = os.path.dirname(project)
activate_this = os.path.join(root, 'env', 'bin', 'activate_this.py')
execfile(activate_this, dict(__file__=activate_this))

import os, sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "esp.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
