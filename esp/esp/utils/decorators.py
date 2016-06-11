
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2009 by the individual contributors
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

from argcache import cache_function
from argcache.function import get_containing_class

from django.http import HttpResponse
from django.db.models import Model

from inspect import getargspec
from functools import wraps
import json

class OptionalDecorator(object):
    """ A simple decorator to turn a function into a no-op.  If the argument evaluates
        to true, it's transparent.  Otherwise it generates a decorator that causes
        the function to always return False. """

    def __init__(self, value, *args, **kwargs):
        self.value = value

    def __call__(self, func, *args, **kwargs):

        def _do_nothing(*args, **kwargs):
            return False

        if hasattr(self, 'value') and self.value:
            return func
        else:
            return _do_nothing

enable_with_setting = OptionalDecorator

def json_response(field_map={}):
    """ Converts a serializable data structure into the appropriate HTTP response.
        Allows changing the field names using field_map, which might be complicated
        if related lookups were used.
    """

    # Here instead of at the top because of circular imports
    from esp.utils.web import render_to_response

    def map_fields(item):
        if isinstance(item, Model):
            item = item.__dict__
        assert(isinstance(item, dict))
        result = {}
        for key in item:
            if key in field_map:
                result[field_map[key]] = item[key]
            else:
                result[key] = item[key]
        return result

    def dec(func):
        @wraps(func)
        def _evaluate(module_obj, request, *args, **kwargs):
            result = func(module_obj, request, *args, **kwargs)
            if isinstance(result, HttpResponse):
                return result
            elif 'json_debug' in request.GET:
                data = json.dumps(result, sort_keys=True, indent=4)
                return render_to_response('utils/jsondebug.html',
                                          request, {'data': data})
            else:
                if field_map is None:
                    new_result = result
                else:
                    new_result = {}
                    for key in result:
                        new_list = []
                        for item in result[key]:
                            new_list.append(map_fields(item))
                        new_result[key] = new_list
                resp = HttpResponse(content_type='application/json')
                json.dump(new_result, resp)
                return resp

        return _evaluate

    return dec


class CachedModuleViewDecorator(object):
    """ Employs some of the techniques used by the cached inclusion tag to
        make caching a simple program module view easier. """

    def __init__(self, func):
        parent_obj = self
        # NOTE: get_containing_class inspects the stack, so we have to
        # call it ourselves. TODO fix this?
        containing_class = get_containing_class()

        def prepare_dec(func):
            self.params, xx, xxx, defaults = getargspec(func)
            self.cached_function = cache_function(func, containing_class=containing_class)

            def actual_func(self, request, tl, one, two, module, extra, prog):
                #   Construct argument list
                param_name_list = ['self', 'request', 'tl', 'one', 'two', 'module', 'extra', 'prog']
                param_list = [self, request, tl, one, two, module, extra, prog]
                args_for_func = []
                for i in range(len(param_list)):
                    if param_name_list[i] in parent_obj.params:
                        args_for_func.append(param_list[i])
                cache_only = 'cache_only' in request.GET
                return parent_obj.cached_function(*args_for_func, cache_only=cache_only)

            return actual_func

        self.inner_func = prepare_dec(func)

    def __call__(self, *args):
        return self.inner_func(*args)

    def __getattr__(self, attr):
        return getattr(self.inner_func, attr)

cached_module_view = CachedModuleViewDecorator
