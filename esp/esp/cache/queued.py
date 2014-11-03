""" General object with queuable actions. """

import types

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

def add_lazy_dependency(self, obj, operation):
    """ If obj is a function (thunk), delay operation; otherwise execute immediately. """
    # XXX: this is temporarily clunky because it's using delay_method in an unintended way.
    # TODO: delete delay_method and do something better here.
    if isinstance(obj, types.FunctionType):
        @delay_method
        def wrapped(self, obj):
            return operation(self, obj())
        wrapped(self, obj)
    else:
        operation(self, obj)
