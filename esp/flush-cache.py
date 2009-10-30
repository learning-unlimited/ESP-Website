#!/usr/bin/python

path_to_esp = '/esp/web/mit/'

# Generic setup code to be able to import esp stuff
import sys
sys.path += [path_to_esp]

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

from django.core.cache import cache

if hasattr(cache, "flush_all"):
	cache.flush_all()
elif hasattr(cache, "_wrapped_cache") and hasattr(cache._wrapped_cache, "flush_all"):
	cache._wrapped_cache.flush_all()
else:
	print "Error: Cache doesn't support flush_all()"
