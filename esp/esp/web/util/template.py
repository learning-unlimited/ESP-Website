
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
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
  Email: web-team@lists.learningu.org
"""

from django import template
from esp.middleware.threadlocalrequest import AutoRequestContext
from esp.cache import cache_function
from django.utils.functional import curry
import random
import warnings

from inspect import getargspec

__all__ = ['cache_inclusion_tag', 'DISABLED']

class Disabled_Cache(object):
    def noop(*args, **kwargs):
        return None

    get = set = delete = noop

DISABLED = Disabled_Cache()

class InclusionTagCacheDecorator(object):

    def __init__(self, register, file_name, context_class=AutoRequestContext,  takes_context=False, **kwargs):
        """
        This function will cache the rendering and output of a inclusion tag for cache_time seconds.

        To use, just do the following::

        from django import template
        from esp.web.util.template import cache_inclusion_tag
        
        register = template.Library()

        def cache_key_func(foo, bar, baz):
            # takes the same arguments as below
            return str(foo)

        @cache_inclusion_tag(register, 'path/to/template.html', cache_key_func=cache_key_func)
        def fun_tag(foo, bar, baz):
            return {'foo': foo}


        The tag will now be cached.
        """
        
        if 'cache_key_func' in kwargs:
            warnings.warn('Cache key function for cache_inclusion_tag is being ignored, now that cache_inclusion_tag uses caching API', DeprecationWarning)

        parent_obj = self

        def prepare_dec(func):
            params, xx, xxx, defaults = getargspec(func)
            from esp.cache.function import describe_func

            if takes_context:
                if params[0] == 'context':
                    params = params[1:]
                else:
                    raise TemplateSyntaxError, "Any tag function decorated with takes_context=True must have a first argument of 'context'"

            class InclusionNode(template.Node):
                def __init__(self, vars_to_resolve):
                    self.vars_to_resolve = vars_to_resolve

                def render_given_args(self, args):

                    dict = func(*args)

                    if not getattr(self, 'nodelist', False):
                        from django.template.loader import get_template, select_template
                        if hasattr(file_name, '__iter__'):
                            t = select_template(file_name)
                        else:
                            t = get_template(file_name)
                        self.nodelist = t.nodelist
                    retVal = self.nodelist.render(context_class(dict, autoescape=self._context.autoescape))

                    return retVal
                render_given_args = cache_function(render_given_args, uid_extra='*'+describe_func(func))  

                def render(self, context):
                    resolved_vars = []
                    for var in self.vars_to_resolve:
                        try:
                            resolved_vars.append(template.resolve_variable(var, context))
                        except:
                            resolved_vars.append(None)

                    if takes_context:
                        args = [context] + resolved_vars
                    else:
                        args = resolved_vars

                    self._context = context

                    return self.render_given_args(args)

            compile_func = curry(template.generic_tag_compiler, params, defaults, func.__name__, InclusionNode)
            compile_func.__doc__ = func.__doc__
            register.tag(func.__name__, compile_func)
            func.cached_function = InclusionNode.render_given_args
            return func

        self.prepare_func = prepare_dec

    def __call__(self, func):
        return self.prepare_func(func)

cache_inclusion_tag = InclusionTagCacheDecorator

