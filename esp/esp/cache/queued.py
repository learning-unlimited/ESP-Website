""" General object with queuable actions. """

import types

from django.db.models import signals, get_model

pending_lookups = {}

def add_lazy_dependency(self, obj, operation):
    """ If obj is a function (thunk), delay operation; otherwise execute immediately. """
    if isinstance(obj, basestring):
        app_label, model_name = obj.split(".")
        model = get_model(app_label, model_name,
                          seed_cache=False, only_installed=False)
        if model:
            operation(model)
        else:
            key = (app_label, model_name)
            value = operation
            pending_lookups.setdefault(key, []).append(value)
    elif isinstance(obj, types.FunctionType):
        import warnings
        warnings.warn("Using lambdas to thunk dependencies is deprecated. Use strings instead.", DeprecationWarning, stacklevel=3)
        # HACK: stick the lambda into pending_lookups as a key,
        # which will be processed in do_all_pending.
        key = obj
        value = operation
        pending_lookups.setdefault(key, []).append(value)
    else:
        operation(obj)

def do_pending_lookups(sender, **kwargs):
    """ Handle any pending dependencies on the sending model. Sent from class_prepared. """
    key = (sender._meta.app_label, sender.__name__)
    for operation in pending_lookups.pop(key, []):
        operation(sender)

signals.class_prepared.connect(do_pending_lookups)

def do_all_pending():
    # process any pending lookups that are actually lambdas.
    for key in pending_lookups:
        assert isinstance(key, types.FunctionType)
        for operation in pending_lookups.get(key, []):
            operation(key())
