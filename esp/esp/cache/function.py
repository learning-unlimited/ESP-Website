""" Decorator to automatically add a cache to a function. """
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

import inspect
import types

from esp.cache.argcache import ArgCache
from esp.cache.marinade import describe_func, get_containing_class

class ArgCacheDecorator(ArgCache):
    """ An ArgCache that gets its parameters from a function. """

    def __init__(self, func, *args, **kwargs):
        """ Wrap func in a ArgCache. """

        ## Keep the original function's name and docstring
        ## If the original function has any more-complicated attrs,
        ## don't bother to maintain them; we have our own attrs,
        ## and merging custom stuff could be dangerous.
        if hasattr(func, '__name__'):
            self.__name__ = func.__name__
        if hasattr(func, '__doc__'):
            self.__doc__ = func.__doc__

        self.func = func
        containing_class = kwargs.pop('containing_class', get_containing_class())
        extra_name = kwargs.pop('extra_name', '')
        name = describe_func(func, containing_class) + extra_name
        params, varargs, keywords, _ = inspect.getargspec(func)
        if varargs is not None:
            raise ESPError("ArgCache does not support varargs.")
        if keywords is not None:
            raise ESPError("ArgCache does not support keywords.")

        super(ArgCacheDecorator, self).__init__(name=name, params=params, *args, **kwargs)

    # TODO: this signature may break if we have a kwarg named `self`
    # (same applies to __call__ below)
    # for now... assume this doesn't happen
    def arg_list_from(self, *args, **kwargs):
        """ Normalizes arguments to get an arg_list. """
        callargs = inspect.getcallargs(self.func, *args, **kwargs)
        return [callargs[param] for param in self.params]

    def __call__(self, *args, **kwargs):
        """ Call the function, using the cache is possible. """
        use_cache = kwargs.pop('use_cache', True)
        cache_only = kwargs.pop('cache_only', False)

        if use_cache:
            arg_list = self.arg_list_from(*args, **kwargs)
            retVal = self.get(arg_list, default=self.CACHE_NONE)

            if retVal is not self.CACHE_NONE:
                return retVal

            if cache_only:
                retVal = None
            else:
                retVal = self.func(*args, **kwargs)
                self.set(arg_list, retVal)
        else:
            retVal = self.func(*args, **kwargs)

        return retVal

    # make bound member functions work...
    def __get__(self, obj, objtype=None):
        """ Python member functions are such hacks... :-D """
        return types.MethodType(self, obj, objtype)


# This is a bit more of a decorator-style name
cache_function = ArgCacheDecorator
