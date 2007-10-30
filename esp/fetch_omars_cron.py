#!/usr/bin/python

import sys
sys.path += ['/esp/esp/']

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

import esp.manage
from esp.money.fetch_omars import fetch_omars

fetch_omars( certfile=sys.argv[1], keyfile=sys.argv[2], cacert=sys.argv[3] )
