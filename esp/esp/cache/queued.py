""" General object with queuable actions. """

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

