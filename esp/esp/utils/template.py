
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2012 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""

""" A loader that looks for templates in the override model. """

import django.template.loaders.cached

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
        return hashlib.md5(contents.encode("utf-8")).hexdigest()
    get_template_hash.depend_on_model('utils.TemplateOverride')
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

    def load_template_source(self, template_name, template_dirs=None):
        """
        Returns a tuple containing the source and origin for the given template
        name. Raises TemplateDoesNotExist Exception if the template override
        for the given template name does not exist.

        Overrides the unimplemented method from the BaseLoader base class.
        """
        from django.conf import settings
        source = Loader.get_override_contents(template_name)
        if source:
            return (source.decode(settings.FILE_CHARSET), DEFAULT_ORIGIN)
        raise TemplateDoesNotExist(template_name)

class CachedLoader(django.template.loaders.cached.Loader):
    """
    Wrapper class that takes a list of template loaders as an argument and
    attempts to load templates from them in order, caching the result.

    A subclass of django.template.loaders.cached.Loader that implements the
    unimplemented load_template_source method from the BaseLoader base class.
    """
    is_usable = True

    def load_template_source(self, template_name, template_dirs=None):
        """
        Returns a tuple containing the source and origin for the given template
        name. Iterates through its list of template loaders in order, calling
        load_template_source() for each of them and returning the first valid
        result. Raises TemplateDoesNotExist Exception if the template for the
        given template name does not exist in any of the template loaders.

        Overrides the unimplemented method from the BaseLoader base class.
        """
        for loader in self.loaders:
            try:
                return loader.load_template_source(template_name, template_dirs=template_dirs)
            except TemplateDoesNotExist:
                pass
        raise TemplateDoesNotExist(template_name)

