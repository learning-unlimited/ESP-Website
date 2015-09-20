
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

from copy import copy
from functools import partial
from inspect import getargspec

from django.template import Context
from django.template.base import generic_tag_compiler, TagHelperNode, Template
from django.utils.itercompat import is_iterable
from django.utils import six

from esp.cache import cache_function
from esp.cache.key_set import is_wildcard
from esp.middleware import ESPError

__all__ = ['cache_inclusion_tag', 'DISABLED']


class Disabled_Cache(object):
    def noop(*args, **kwargs):
        return None

    get = set = delete = noop

DISABLED = Disabled_Cache()


def _render_cache_key_set_mapper(params):
    """Return a function suitable for use as a depend_on_cache mapping_func

    Given the params of a function, return a mapping_func taking a key_set for
    the function, and returning a key_set for
    CacheInclusionNode.render_given_args."""
    def key_set(**kwargs):
        if kwargs == {}:
            # If the key set is empty, we can just flush everything.
            return {}
        elif any(is_wildcard(val) for val in kwargs.itervalues()):
            # Flush everything if we got a wildcard, because the argcache API
            # doesn't support a more precise expiry.
            return {}
        else:
            # Otherwise, prepare a key set embedding the argument list in the
            # 'args' key
            return {'resolved_args': [kwargs.get(key) for key in params]}
    return key_set


# HERE BE DRAGONS!
#
# This code is partially copied from the django source for
# django.template.base.Library.inclusion_tag, and was last updated for Django
# 1.8.  All changes from the Django source we're copying should be commented
# inline with "# CHANGED:" to make this easy to update.
#
# The reason we're here in the first place is that just caching a function,
# then passing it to register.inclusion_tag will cache the computation of the
# tag's context, but not its rendering, which doesn't do us much good.  So we
# have to roll our own node that modifies InclusionNode, which django doesn't
# really support.  (In fact, we can't even inherit from InclusionNode, because
# it's defined *inside* register.inclusion_tag.)  In addition, template
# rendering is complicated, and caching a part of it has some weird subtleties
# that we have to deal with.
#
# The process of rendering an inclusion tag goes roughly like this:
#                       1                 2                    3
#    tag args, context --> function args --> template context --> rendered node
#
# In Django's InclusionNode, the render() method does all of these.  We don't
# want our caching to depend on the tag's surrounding context, because that
# will probably never be the same twice, so we can't cache step 1.  That's
# okay, because it's fast, and not really a part of the computation one would
# expect to be done by the tag -- it belongs to the surrounding context, and
# the computation model just happens to put it inside the tag.
#
# So we want to cache steps 2 and 3.  (2 is of course just our underlying
# function.)  We might as well cache them as a single step, because it's easier
# that way.  But the problem is that we don't know the args of the underlying
# function here, and argcache doesn't support *args/**kwargs, so we can't
# actually write a function which takes the same argspec as the underlying
# function and pass it to argcache.
#
# Now we *can* just write a function which takes in a list of arguments and
# returns a rendered node, and that's what we do (render_given_args).  But that
# function won't have the argspec that the user expects, so they can't easily
# add cache dependencies to it.  (It's also suboptimal, because we won't be
# able to expire argument-by-argument, but we'll just have to live with that
# one.  So we *also* set up a cache for our underlying function, and then wire
# up the cache of render_given_args to depend on it.
#
# Beyond that, it's just a bunch of copy-pasting and inserting cache code, with
# a bunch of subtleties and a few dirty tricks, commented inline.
#
# TODO(benkraft): once our version of Django contains 655f5249 (which I believe
# will be in 1.9) this will need to be rewritten to match Django's version
# again.  I hope we will be able to simplify it by inheriting from
# InclusionNode instead of copying it.  But a lot of the issues that cause us
# to have to change more code than just adding some `cache_function`s will
# still apply, so we may not be so lucky.
#
# TODO(benkraft): figure out if there's a remotely clean way of doing this.
# Perhaps even file a bug against django to have them make it easier on their
# side.
#
# CHANGED: changed self to register in the function definition, and changed the
# function name to cache_inclusion_tag
def cache_inclusion_tag(register, file_name, takes_context=False, name=None):
    """
    Register a callable as an inclusion tag, cachedly.

    This function will cache the rendering of an inclusion tag.  It works more
    or less like `register.inclusion_tag`, subject to the gotchas below.
    You may use the caching API to add dependencies for automatic invalidation
    by accessing the 'cached_function' attribute of the decorated function.
    For example:

    from django import template
    from esp.web.util.template import cache_inclusion_tag

    register = template.Library()

    @cache_inclusion_tag(register, 'path/to/template.html')
    def fun_tag(foo, bar, baz):
        return {'foo': foo}
    fun_tag.cached_function.depend_on_row(lambda: SomeModel, lambda some_instance: {'foo': some_instance.foo})

    GOTCHAS:
      * cache_inclusion_tag will always pass a Context through to the template,
        no matter what type of context is passed to it.  This is to prevent
        having non-explicit access to e.g. RequestContext.request, which could
        cause caching bugs and let one user see data from another, if we're not
        careful.  If you want to have access to any request vars in a
        cache_inclusion_tag, you must pass them through manually.
      * `{% csrf_token %}` won't work inside a cache_inclusion_tag.  We
        shouldn't be caching a csrf_token, ever.  If you need one, don't cache
        your inclusion tag, or populate it client-side.
      * cache_inclusion tags doesn't support passing keyword arguments.  This
        is due to argcache limitations.
      * template tags that make heavy use of render_context might not work
        properly, since using render_context can make identical calls to the
        same tag render differently.  If you don't know what any of that means,
        it probably won't hurt you; as of Django 1.8, the only built-in tag
        that might require care is `{% cycle %}`.
    """
    def dec(func):
        # In our case varargs and varkw had better be None, or else
        # cache_function will fail.
        params, varargs, varkw, defaults = getargspec(func)
        # CHANGED: added the following line
        cached_func = cache_function(func)

        class CachedInclusionNode(TagHelperNode):
            # CHANGED: added the following lines, which makes sure that the
            # cache for render_given_args will not depend on self in a
            # nontrivial way.  This is pretty dangerous and we deserve whatever
            # we get, but I think we'll be okay; basically the only things we
            # will reference on self are the template engine (which should
            # ~never change) and the context we're going to hide (see below).
            def __marinade__(self):
                return '<CachedInclusionNode>'

            def render(self, context):
                """
                Renders the specified template and context. Caches the
                template object in render_context to avoid reparsing and
                loading when used in a for loop.
                """
                resolved_args, resolved_kwargs = self.get_resolved_arguments(context)
                # CHANGED: added the conditional safety-check.
                if resolved_kwargs:
                    raise ESPError("Due to ArgCache limitations, "
                                   "cache_inclusion_tag does not support "
                                   "passing keyword arguments.")
                # CHANGED: moved the remainder of the work of the function into
                # render_given_args so we can cache it.  We sneakily pass
                # context around where argcache won't see it -- as an attribute
                # of self (which argcache won't noticed due to our
                # __marindate__ above), rather than as a proper function
                # parameter.  As above, this is dangerous, but we will only
                # ever access a whitelisted set of attributes on it.
                self._context = context
                return self.render_given_args(resolved_args)

            # CHANGED: this was previously inlined in render(), we break it out
            # into a separate function so we can cache it.  Again, pull context
            # back off of self.  Remember not to access anything on it that is
            # likely to change between invocations.
            def render_given_args(self, resolved_args):
                context = self._context
                # CHANGED: func -> cached_func
                _dict = cached_func(*resolved_args)

                t = context.render_context.get(self)
                if t is None:
                    if isinstance(file_name, Template):
                        t = file_name
                    elif isinstance(getattr(file_name, 'template', None), Template):
                        t = file_name.template
                    elif not isinstance(file_name, six.string_types) and is_iterable(file_name):
                        t = context.template.engine.select_template(file_name)
                    else:
                        t = context.template.engine.get_template(file_name)
                    context.render_context[self] = t
                # CHANGED: new_context = context.new(_dict) to the following
                # five lines.  We don't want to copy the context because it
                # might be a RequestContext, even if the tag's cache doesn't
                # depend on this user.  This would be Very Bad; it could cause
                # the cache to leak data about one user to another user.  So we
                # require using a plain Context, and copy a whitelisted set of
                # attrs over, rather than using copy().
                new_context = Context(_dict)
                for attr in ['autoescape', 'use_l10n', 'use_tz', 'template']:
                    if hasattr(context, attr):
                        setattr(new_context, attr, getattr(context, attr))
                new_context.render_context = copy(context.render_context)
                # CHANGED: removed copying the csrf_token over to the
                # new_context, because we should never do that.  If you need a
                # csrf_token in an inclusion tag, you'll have to generate your
                # own with AJAX.
                return t.render(new_context)

            # CHANGED: added the following lines
            render_given_args = cache_function(
                render_given_args, extra_name='*' + cached_func.name)
            render_given_args.get_or_create_token(('resolved_args',))
            render_given_args.depend_on_cache(
                cached_func, _render_cache_key_set_mapper(params))
            render_given_args.depend_on_model('utils.TemplateOverride')

        function_name = (name or
            getattr(func, '_decorated_function', func).__name__)
        compile_func = partial(generic_tag_compiler,
            params=params, varargs=varargs, varkw=varkw,
            defaults=defaults, name=function_name,
            takes_context=takes_context, node_class=CachedInclusionNode)
        compile_func.__doc__ = func.__doc__
        # CHANGED: self -> register on the following line
        register.tag(function_name, compile_func)
        # CHANGED: added the following line to allow adding cache dependencies
        func.cached_function = cached_func
        return func
    return dec
