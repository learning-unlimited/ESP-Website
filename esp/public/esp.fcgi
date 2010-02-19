#!/usr/bin/python
import sys, os

# Add a custom Python path.
sys.path.insert(0, "/esp/web_git/stanford/esp/")

# Switch to the directory of your project. (Optional.)
os.chdir("/esp/web_git/stanford/esp/")

# Set the DJANGO_SETTINGS_MODULE environment variable.
os.environ['DJANGO_SETTINGS_MODULE'] = "esp.settings"

from django.core.servers.fastcgi import runfastcgi

import cProfile
cProfile.run('runfastcgi(method="prefork", daemonize="false")', '/tmp/stanford-profile-log.txt')
