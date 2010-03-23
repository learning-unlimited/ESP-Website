class defaultclass(object):
    """
    Allows you to have a class with alternate implementations;
    and pick the implementation that you want at runtime using:
    MyCls[key]()
    or similar.
    """
    _registered_instances = {}

    def __init__(self, target_cls):
        self._target_cls = target_cls 
        self._registered_instances = {}
    
    @property
    def real(self):
        """ We don't look like the class that we're supposed to look like.  Return the class that we're supposed to look like. """
        return self._target_cls
    
    def __setitem__(self, key, val):
        """ Register a handler for this variant of the class.  Note that key must be hashable. """
        self._registered_instances[key] = val

    def __getitem__(self, key):
        """ Get the handler for the specified variant of the class, or cls if none exists. """
        if key in self._registered_instances:
            return self._registered_instances[key]
        return self

    def __delitem__(self, key):
        """ Delete the handler for the specified variant of the class. """
        del self._registered_instances[key]

    def __call__(self, *args, **kwargs):
        """ If we're called directly, generate a new instance of our default class """
        return self._target_cls(*args, **kwargs)

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        else:
            return getattr(self.real, name)
