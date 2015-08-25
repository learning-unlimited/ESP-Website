
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
  Email: web-team@learningu.org
"""

from django import template
from django.template.base import generic_tag_compiler
from django.template import Context
from esp.middleware.threadlocalrequest import AutoRequestContext
from esp.cache import cache_function
from esp.cache.key_set import wildcard, is_wildcard
from functools import partial
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

    def __init__(self, register, file_name, context_class=Context, takes_context=False, disable=False, **kwargs):
        """
        This function will cache the rendering and output of a inclusion tag for cache_time seconds.
        You may use the caching API to add dependencies for automatic invalidation by accessing the
        'cached_function' attribute of the decorated function.

        To use, just do the following:

        from django import template
        from esp.web.util.template import cache_inclusion_tag
        
        register = template.Library()

        @cache_inclusion_tag(register, 'path/to/template.html')
        def fun_tag(foo, bar, baz):
            return {'foo': foo}
        fun_tag.cached_function.depend_on_row(lambda: SomeModel, lambda some_instance: {'foo': some_instance.foo})

        The tag will now be cached.  Note that you may need to include the keyword argument context_class=AutoRequestContext
        (e.g. esp.middleware.threadlocalrequest.AutoRequestContext) in order to use {{ request }} variables in
        the template.  This should not be used in proxy-cached views since it accesses session data and causes
        the Vary: Cookie header to be set.
        """
        
        if 'cache_key_func' in kwargs:
            warnings.warn('Cache key function for cache_inclusion_tag is being ignored, now that cache_inclusion_tag uses caching API', DeprecationWarning)

        parent_obj = self
        # NOTE: get_containing_class inspects the stack, so we have to
        # call it ourselves. TODO fix this?
        from esp.cache.function import get_containing_class
        containing_class = get_containing_class()

        def prepare_dec(func):
            params, xx, xxx, defaults = getargspec(func)
            cached_function = cache_function(func, containing_class=containing_class)

            if takes_context:
                if params[0] == 'context':
                    params = params[1:]
                else:
                    raise template.TemplateSyntaxError, "Any tag function decorated with takes_context=True must have a first argument of 'context'"

            class InclusionNode(template.Node):

                def __init__(in_self, takes_context, vars_to_resolve, kwargs):
                    in_self.vars_to_resolve = vars_to_resolve
                    
                def __str__(in_self):
                    return '<IN>'

                def render_given_args(in_self, args):
                    dict = cached_function(*args)

                    if not getattr(in_self, 'nodelist', False):
                        from django.template.loader import get_template, select_template
                        if hasattr(file_name, '__iter__'):
                            t = select_template(file_name)
                        else:
                            t = get_template(file_name)
                        in_self.nodelist = t.nodelist
                    return in_self.nodelist.render(context_class(dict, autoescape=in_self._context.autoescape))

                if not disable:
                    # TODO: fix how describe_func inspects the stack
                    # so that we don't have to call it manually here
                    render_given_args = cache_function(render_given_args, extra_name='*'+cached_function.name)
                    render_given_args.get_or_create_token(('args',))
                    def render_map(**kwargs):
                        
                        #   If the key set is empty, we can just flush everything.
                        if kwargs == {}:
                            result = {}
                        else:
                            #   Otherwise, prepare a key set embedding the argument list in the 'args' key
                            result_args = []
                            for key in params:
                                if key in kwargs:
                                    result_args.append(kwargs[key])
                                else:
                                    result_args.append(None)
                            result = {'args': result_args}
                            
                        #   Flush everything if we got a wildcard
                        for key in kwargs:
                            if is_wildcard(kwargs[key]):
                                result = {}
                        return result
                        
                    render_given_args.depend_on_cache(cached_function, render_map)

                def render(in_self, context):
                    resolved_vars = []
                    for var in in_self.vars_to_resolve:
                        try:
                            resolved_vars.append(var.resolve(context))
                        except:
                            print 'Could not resolve %s' % var                            
                            resolved_vars.append(None)

                    if takes_context:
                        args = [context] + resolved_vars
                    else:
                        args = resolved_vars

                    in_self._context = context

                    return in_self.render_given_args(args)

            # generic_tag_compiler is private API
            compile_func = partial(generic_tag_compiler,
                params=params, varargs=[], varkw={},
                defaults=defaults, name=func.__name__,
                takes_context=takes_context, node_class=InclusionNode)
            compile_func.__doc__ = func.__doc__
            register.tag(func.__name__, compile_func)
            func.cached_function = cached_function
            return func

        self.prepare_func = prepare_dec

    def __call__(self, func):
        return self.prepare_func(func)

cache_inclusion_tag = InclusionTagCacheDecorator

