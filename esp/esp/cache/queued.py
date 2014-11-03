""" General object with queuable actions. """

import types

from django.db.models import signals, get_model

def delay_method(func):
    def add_to_queue(self, *args, **kwargs):
        self._methods_queue.append( (func, args, kwargs) )
    return add_to_queue

class WithDelayableMethods(object):
    def __init__(self, *args, **kwargs):
        self._methods_queue = []
        super(WithDelayableMethods, self).__init__(*args, **kwargs)

    def run_all_delayed(self):
        for func, args, kwargs in self._methods_queue:
            func(self, *args, **kwargs)
        self._methods_queue = []

pending_lookups = {}

def add_lazy_dependency(self, obj, operation):
    """ If obj is a function (thunk), delay operation; otherwise execute immediately. """
    # XXX: this is temporarily clunky because it's using delay_method in an unintended way.
    # TODO: delete delay_method and do something better here.
    if isinstance(obj, basestring):
        app_label, model_name = obj.split(".")
        model = get_model(app_label, model_name,
                          seed_cache=False, only_installed=False)
        if model:
            operation(self, model)
        else:
            key = (app_label, model_name)
            value = (self, operation)
            pending_lookups.setdefault(key, []).append(value)
    elif isinstance(obj, types.FunctionType):
        @delay_method
        def wrapped(self, obj):
            return operation(self, obj())
        wrapped(self, obj)
    else:
        operation(self, obj)

def do_pending_lookups(sender, **kwargs):
    """ Handle any pending dependencies on the sending model. Sent from class_prepared. """
    key = (sender._meta.app_label, sender.__name__)
    for (self, operation) in pending_lookups.pop(key, []):
        operation(self, sender)

signals.class_prepared.connect(do_pending_lookups)
