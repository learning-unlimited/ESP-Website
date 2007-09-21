#!/usr/bin/env python
""" Allows a user to tweak the queue settings on the fly.

Usage:

%s [--max_inside <MAX_INSIDE>] [--timeout <TIMEOUT>] [--refresh_time <REFRESH_TIME>] [--delay <DELAY>] [--status] [--clear]

Options:
    --max_inside: The number of people you want in the site.
    --timeout: How much inactivity before someone is logged out.
    --refresh_time: How long someone on the queue is automatically refreshed.
  -or-
    --status: Display the status and exit.
  -or-
    --delay: Display the status DELAY seconds.
  -or-
    --clear-all: Purge all queue information.
  -or-
    --inside: Show people inside.
  -or-
    --queue: Show people waiting on the queue.
"""


import sys, re, time, itertools, gc

path_re = re.compile('^(.*)/esp/queue.*$')
sys.path = [path_re.sub(r'\1', sys.path[0])] + sys.path

from django.core.management import setup_environ
try:
    import esp.settings
except ImportError:
    print "Error: You need to run this from the command line!"
    sys.exit(1)

setup_environ(esp.settings)

from esp.queue.models import QueueItem
from esp.utils.memdb import mem_db


def clear_queue():
    q = QueueItem()
    for key in itertools.chain(q.inside_keys, q.queue_keys):
        mem_db.delete(key)
    q.inside_keys = []
    q.queue_keys = []

def tweak(max_inside=None, timeout=None, refresh_time=None):
    q = QueueItem()
    old_max_inside = q.max_inside
    old_timeout = q.timeout
    old_refresh_time = q.refresh_time

    if max_inside:
        q.max_inside = int(max_inside)

    if timeout:
        q.timeout = int(timeout)

    if refresh_time:
        q.refresh_time = float(refresh_time)

    print """


QUEUE STATUS REPORT:
====================

Max Inside: %s (was: %s)
Timeout: %s seconds (was %s)
Refresh Time: %s seconds (was %s)

Number in queue: %s
Number on the site: %s""" % (q.max_inside, old_max_inside,
       q.timeout, old_timeout,
       q.refresh_time, old_refresh_time,
       len(q.queue_keys), len(q.inside_keys))
    del q
    gc.collect()

def display_help():
    print __doc__ % sys.argv[0]

if __name__ == '__main__':
    args = sys.argv[1:]
    variables = ('max_inside','timeout','refresh_time',)
    kwargs = {}

    TWEAK = False

    try:
        delay_index = args.index('--delay')
        delay = float(args[delay_index + 1])
    except (ValueError, IndexError, TypeError):
        pass
    else:
        while True:
            tweak()
            time.sleep(delay)

    if '--inside' in args or '--queue' in args:
        q = QueueItem()
        info, bots = [], []
        if '--inside' in args:
            keys = q.inside_keys
        else:
            keys = q.queue_keys

        for key in keys:
            retVal = mem_db.get(key)
            if retVal is not None:
                cur_val = '\t\t'.join(mem_db.get(key).split(',',2)[1:])
                cur_val_lower = cur_val.lower()
                if 'bot' in cur_val_lower or 'crawl' in cur_val_lower or 'curl' in cur_val_lower or 'wget' in cur_val_lower or 'spider' in cur_val_lower:
                    bots.append(cur_val)
                else:
                    info.append(cur_val)

        info = bots + info

        print """
The %s people inside the site, at the moment:
=============================================

""" % (len(info))

        print '\n'.join(info)
        sys.exit(0)

    for i, arg in enumerate(args):
        if arg[2:].lower() in variables and (i + 1) < len(args):
            TWEAK = True
            kwargs[arg[2:].lower()] = args[i + 1]

    if not kwargs:
        if '--status' in args:
            TWEAK = True
            kwargs = {}

    if '--clear-all' in args:
        clear_queue()
        sys.exit(0)

    if TWEAK:
        tweak(**kwargs)
    else:
        display_help()
