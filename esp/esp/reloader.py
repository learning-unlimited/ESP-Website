# Michael Axiak
# Released under GPL v2+.
# Some code borrowed from Chris Lamb <lamby@debian.org> [1], which is released under BSD.
#
# 1: http://code.djangoproject.com/attachment/ticket/9722/0002-Add-support-for-pyinotify.patch

import os
import sys
import datetime
import threading

try:
    import pyinotify
except ImportError:
    raise ImportError("pyinotify not found. On debian based systems: try apt-get install python-pyinotify.")

from django.core import signals

__all__ = ('start_reloader',)

_last_update = None

def inotify_code_changed():
    files = set()
    for filename in filter(lambda v: v, map(lambda m: getattr(m, "__file__", None), sys.modules.values())):
        if filename.endswith(".pyc") or filename.endswith(".pyo"):
            filename = filename[:-1]
        if not os.path.exists(filename):
            continue # File might be in an egg, so it can't be reloaded.
        files.add(filename)

    wm = pyinotify.WatchManager()
    notifier = pyinotify.Notifier(wm)
    min_update_interval = datetime.timedelta(seconds = 1)
    def update_watch(sender=None, **kwargs):
        global _last_update
        if _last_update is not None and \
           datetime.datetime.now() - _last_update < min_update_interval:
           return

        _last_update = datetime.datetime.now()

        mask = pyinotify.EventsCodes.IN_MODIFY \
 		             | pyinotify.EventsCodes.IN_DELETE \
 		             | pyinotify.EventsCodes.IN_ATTRIB \
 		             | pyinotify.EventsCodes.IN_MOVED_FROM \
 		             | pyinotify.EventsCodes.IN_MOVED_TO \
 		             | pyinotify.EventsCodes.IN_CREATE

        for path in files:
            wm.add_watch(path, mask)

    signals.request_finished.connect(update_watch)
    update_watch()

    # Block forever
    notifier.check_events(timeout=None)
    notifier.stop()

    # If we are here the code must have changed.
    return True

def reloader_thread():
    while True:
        if inotify_code_changed():
            os._exit(3)

def start_reloading():
    t = threading.Thread(target=reloader_thread)
    t.daemon = True
    t.start()
