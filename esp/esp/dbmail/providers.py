"""Registry of email variable providers that can be stored by reference.

``MessageVars`` used to persist its provider by pickling the whole object.
In practice every provider is a saved model instance, so it can be stored as
an ``(app_label.ModelName, pk)`` pair instead and re-fetched from the database
on read -- no deserialization of executable data required.

Providers are keyed by ``"<app_label>.<ModelName>"`` rather than by bare class
name, so two models with the same name in different apps cannot be confused
for one another.  ``apps.get_model()`` resolves lazily, which keeps this
module free of import cycles with ``esp.dbmail.models``.
"""

from django.apps import apps

__all__ = ('PROVIDER_REGISTRY', 'provider_key', 'is_registered',
           'get_provider_class', 'get_provider_instance')

#   Models whose instances may be stored as a MessageVars provider.
#   Add an entry here to register a new provider.
PROVIDER_REGISTRY = frozenset((
    'program.Program',
    'program.ClassSection',
    'program.ClassSubject',
    'program.StudentRegistration',
    'users.ESPUser',
))


def provider_key(obj):
    """Return the registry key for ``obj``, or None if it is not a model."""
    meta = getattr(obj, '_meta', None)
    if meta is None:
        return None
    return f'{meta.app_label}.{meta.object_name}'


def is_registered(key):
    return key in PROVIDER_REGISTRY


def get_provider_class(key):
    """Look up a provider model class from the registry by key."""
    if not is_registered(key):
        raise TypeError(
            f"Provider model '{key}' is not registered as a safe email "
            f"provider.  Registered providers: {sorted(PROVIDER_REGISTRY)}"
        )
    app_label, model_name = key.split('.', 1)
    return apps.get_model(app_label, model_name)


def get_provider_instance(key, pk):
    """Fetch a registered provider by primary key, or None if it is gone."""
    provider_class = get_provider_class(key)
    try:
        return provider_class.objects.get(pk=pk)
    except provider_class.DoesNotExist:
        return None
