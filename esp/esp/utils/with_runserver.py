#!/usr/bin/python

from multiprocessing import Process
from django.core.management import call_command
import time
import socket
import random

TEST_HOSTNAME='127.0.0.1'
TEST_PORT=None

def with_runserver(fn):
    """
    Starts up a dev server; calls fn with the URL of the root of the server
    """
    def _wrapped():
        # Set the target hostname and port
        hostname = TEST_HOSTNAME if TEST_HOSTNAME else '127.0.0.1'
        port = TEST_PORT if TEST_PORT else random.randint(1024,65535)
        target = "%s:%s" % (hostname, port)

        # Start a dev server
        p = Process(target=call_command, args=('runserver', target), kwargs={'use_reloader': False})
        p.start()

        # Wait for the dev server to start
        while (True):
            try:
                s = socket.create_connection((hostname, port))
                ## If the above command didn't die with an exception, the server's up now
                s.close()
                break
            except:
                ## Give the runserver process a few more CPU cycles
                time.sleep(0.01)

        fn("http://" + target)

        # Kill off the dev server, so we can use it later
        p.terminate()

    return _wrapped
