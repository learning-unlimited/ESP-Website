"""
A registry for email variable providers to allow safe serialization.

All model imports are done lazily inside functions to avoid circular imports
between esp.dbmail.models and esp.program.models.
"""

# Maps class name string -> dotted import path for lazy loading.
# To register a new provider, add an entry here.
PROVIDER_REGISTRY = {
    'Program':              'esp.program.models.Program',
    'ClassSection':         'esp.program.models.ClassSection',
    'TeacherRegistration':  'esp.program.models.TeacherRegistration',
    'StudentRegistration':  'esp.program.models.StudentRegistration',
    'ESPUser':              'esp.users.models.ESPUser',
}


def _import_class(dotted_path):
    """Lazily import a class from a dotted module path."""
    module_path, class_name = dotted_path.rsplit('.', 1)
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def get_provider_class(name):
    """Look up a provider class from the registry by name."""
    if name not in PROVIDER_REGISTRY:
        raise TypeError(
            f"Provider class '{name}' is not registered as a safe email provider. "
            f"Registered providers: {list(PROVIDER_REGISTRY.keys())}"
        )
    return _import_class(PROVIDER_REGISTRY[name])


def get_provider_instance(class_name, pk):
    """Instantiate a registered provider using its primary key."""
    provider_class = get_provider_class(class_name)
    try:
        return provider_class.objects.get(pk=pk)
    except provider_class.DoesNotExist:
        return None
