#!/usr/bin/env python2

# Run a query against a site in a given directory.
# usage e.g. $0 /lu/sites/smith "print Program.objects.count()"
#            $0 /lu/sites/smith "$(cat script.py)"
# Intended primarily to be used by run_queries.sh.

import sys
sys.path.insert(0, sys.argv[1]+'/esp/useful_scripts')

try:
    from script_setup import *
except:
    print "ERROR: no script_setup.py"
    sys.exit(1)

try:
    exec sys.argv[2]
except:
    print "ERROR: code failed to run"
    raise
