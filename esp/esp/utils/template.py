
""" A loader that looks for templates in the override model. """

from django.template.loader import BaseLoader, get_template_from_string
from django.template import TemplateDoesNotExist

from esp.utils.models import TemplateOverride
from esp.cache import cache_function

import hashlib

DEFAULT_ORIGIN = 'esp.utils.template cached loader'

INVALID_CONTENTS = ''
INVALID_HASH = hashlib.md5(INVALID_CONTENTS).hexdigest()

class Loader(BaseLoader):
    is_usable = True
    
    def __init__(self, *args, **kwargs):
        self.cache = {}

    """ 
        There may be multiple processes running and they all need their caches invalidated
        when a template override is saved.  This is not done by Django's cached template loader.
        The compiled template cannot be stored directly in memcached since Template instances
        contain bound methods.  So, we keep the hash of the template contents in memcached
        and the Template object itself in a local dictionary.
    """
    @cache_function
    def get_template_hash(template_name):
        contents = Loader.get_override_contents(template_name)
        return hashlib.md5(contents).hexdigest()
    get_template_hash.depend_on_row(lambda: TemplateOverride, lambda to: {'template_name': to.name})
    get_template_hash = staticmethod(get_template_hash)

    @staticmethod
    def get_override_contents(template_name):
        qs = TemplateOverride.objects.filter(name=template_name)
        if qs.exists():
            return qs.order_by('-version').values_list('content', flat=True)[0]
        return ''

    def load_template(self, template_name, template_dirs=None):
        hash_val = Loader.get_template_hash(template_name)
        if hash_val == INVALID_HASH:
            raise TemplateDoesNotExist('Template override not found')
        if hash_val not in self.cache:
            template = get_template_from_string(Loader.get_override_contents(template_name), None, template_name)
            self.cache[hash_val] = (template, DEFAULT_ORIGIN)
        return self.cache[hash_val]
    load_template.is_usable = True

