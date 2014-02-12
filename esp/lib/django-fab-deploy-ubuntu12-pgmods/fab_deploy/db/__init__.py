# -*- coding: utf-8 -*-
from __future__ import absolute_import
from fabric.api import env
from taskset import TaskSet

def get_backend():
    """ Returns a module with current VCS """
    db = env.conf.DB_BACKEND
    if isinstance(db, TaskSet):
        return db

    # XXX: do we really need string-based configuration?
    name = db
    mod = __import__(name, fromlist=name.split('.')[1:])
    return mod.instance
