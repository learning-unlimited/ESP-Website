""" Lame hack to ensure all caches are inserted. """

#   Attempt to make newer versions of Django properly realize that this module
#   does not have models.
__path__ = ''

# This is in a separate app because example caches may be in unit tests and
# whatnot for esp.cache. This is probably fine if done properly, but I'd rather
# not have to think about that.

import sys
from django.conf import settings
from esp.cache.registry import _finalize_caches, _lock_caches

# Make sure everything's already imported

#Initializing the model cache for customforms
from esp.customforms.linkfields import cf_cache
cf_cache._populate()

# Import views files from INSTALLED_APPS
for app_name in settings.INSTALLED_APPS:
    if app_name != 'esp.cache_loader':
        __import__(app_name, {}, {}, ['models'])
    # HACK: Duplicate esp.foo in sys.modules as foo.
    # This lets console users type "import program.models"
    # As shorthand for "import esp.program.models".
    # In the code you should of course still write out the "esp."
    if app_name.startswith('esp.'):
        for key, value in sys.modules.items():
           if key.startswith(app_name):
               sys.modules[key[4:]] = value

#   Make sure template override cache is registered
from esp.utils.template import Loader

#   Make sure all cached inclusion tags are registered
from esp.utils.inclusion_tags import *

# import esp.cache.test

# Fix up the queued events
_finalize_caches()
_lock_caches()
