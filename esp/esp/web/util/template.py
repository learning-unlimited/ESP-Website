
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""

from django.core.cache import cache
from django import template
from django.utils.functional import curry

from inspect import getargspec

__all__ = ['cache_inclusion_tag']

def cache_inclusion_tag(register, file_name, cache_key_func=None, cache_time=99999, context_class=template.Context,  takes_context=False, cache_obj=cache):
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
    
    def dec(func):
        params, xx, xxx, defaults = getargspec(func)
        if takes_context:
            if params[0] == 'context':
                params = params[1:]
            else:
                raise TemplateSyntaxError, "Any tag function decorated with takes_context=True must have a first argument of 'context'"

        class InclusionNode(template.Node):
            def __init__(self, vars_to_resolve):
                self.vars_to_resolve = vars_to_resolve

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

                if cache_key_func:
                    cache_key = cache_key_func(*args)
                    if isinstance(cache_key, (tuple, list)):
                        cache_dict_key, cache_key = cache_key
                    else:
                        cache_dict_key = None
                else:
                    cache_key = None

                if cache_dict_key is not None:
                    cache_dict = cache_obj.get(cache_dict_key)
                    if cache_dict is None: cache_dict = {}

                if cache_key is not None:
                    if cache_dict_key is not None:
                        retVal = cache_dict.get(cache_key, None)
                    else:
                        retVal = cache_obj.get(cache_key)
                    if retVal is not None:
                        return retVal

                dict = func(*args)

                if not getattr(self, 'nodelist', False):
                    from django.template.loader import get_template, select_template
                    if hasattr(file_name, '__iter__'):
                        t = select_template(file_name)
                    else:
                        t = get_template(file_name)
                    self.nodelist = t.nodelist
                retVal = self.nodelist.render(context_class(dict))
                if cache_key is not None:
                    if cache_dict_key is None:
                        cache_obj.set(cache_key, retVal, cache_time)
                    else:
                        cache_dict[cache_key] = retVal
                        cache_obj.set(cache_dict_key, cache_dict, cache_time)
                return retVal

        compile_func = curry(template.generic_tag_compiler, params, defaults, func.__name__, InclusionNode)
        compile_func.__doc__ = func.__doc__
        register.tag(func.__name__, compile_func)
        return func
    return dec
