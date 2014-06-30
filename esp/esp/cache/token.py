""" Tokens for bulk-deleting things. """
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
  Email: web-team@lists.learningu.org
"""

import random

from django.core.cache import cache
from django.db.models import signals
from django.dispatch import Signal

from esp.cache.marinade import marinade_dish
from esp.cache.key_set import has_wildcard, wildcard, specifies_key
from esp.middleware import ESPError

__all__ = ['Token', 'ExternalToken']

global_cache_time = 86400

# Tokens and handles are separated so we can do things like share model-row
# tokens, etc. In general, a token represents an event.

# Provide multiple versions, to avoid having to reconvert a ton
#
# Chain: args --_filter_args--> filt --key--> key
#      original args    just the relevant    final string

class Token(object):
    """ A little token to prove you were saved after an event occurred.  Think
    of it as an authentication cookie. Tokens are parametrized by a subset of
    the original cache's arguments. """

    def __init__(self, name, provided_params, cache=cache):
        self.name = name
        self.cache = cache
        # This should be immutable, also I want to hash it
        if isinstance(provided_params, list):
            provided_params = tuple(provided_params)
        self.provided_params = provided_params

    def filt_param(self, i):
        """ Returns the name of this token's ith parameter. """
        return self.cache_obj.params[self.provided_params[i]]

    def _filter_args(self, args):
        """ Returns only the arguments this Token cares about. """
        return [ args[i] for i in self.provided_params ]

    def key_set_from_filt(self, filt):
        """ Converts from filtered arguments to a keyset. """
        # This WILL cause a KeyError if the keyset is not contained in this
        # Token. All uses of delete_key_set should check contains first
        key_set = {}
        for i,arg in enumerate(filt):
            key_set[self.filt_param(i)] = arg
        return key_set

    def filt_from_key_set(self, key_set):
        """ Converts a keyset to a filt. """
        filt = []
        for i in self.provided_params:
            filt.append(key_set[self.cache_obj.params[i]])
        return filt

    def contains(self, key_set):
        """ Given a key_set, returns whether it is contained in a subset provided by this token. """
        for i in self.provided_params:
            if not specifies_key(key_set, self.cache_obj.params[i]):
                return False
        return True

    def key(self, args):
        """ Given arguments, returns a key."""
        return self.key_filt(self._filter_args(args))

    def key_filt(self, filt):
        """ Given filtered arguments, returns a key."""
        return 'TOKEN__' + self.name + '|' + ':'.join([marinade_dish(arg) for arg in filt])

    def delete_key_set(self, key_set, send_signal=True):
        """ Given a filtered set of arguments, deletes things. """
        self.delete_filt(self.filt_from_key_set(key_set), send_signal)
    delete_key_set.alters_data = True

    def delete_filt(self, filt, send_signal=True):
        """ Given a filtered set of arguments, deletes things. """
        # Check if this is a single item...
        if has_wildcard(filt):
            raise ESPError("Tried to delete an argument set with a wildcard.")
        self.cache.delete(self.key_filt(filt))
        # Send the signal...
        if send_signal:
            key_set = self.key_set_from_filt(filt)
            self.cache_obj.send(key_set=key_set)
    delete_filt.alters_data = True

    def value_args(self, args):
        """ Returns a token value, based on function arguments. """
        return self.value_filt(self._filter_args(args))

    def value_filt(self, filt):
        """ Returns a token value, based on filtered arguments. """
        return self.value_key(self.key_filt(filt))

    def value_key(self, key):
        """ Returns and, if necessary, creates a token value at this key. """
        token = self.cache.get(key)
        if token is None:
            token = random.randint(0, 1048575)
            self.cache.add(key, token, global_cache_time)
        return token

    def __str__(self):
        return 'Token %s' % self.name

# A proxy token of sorts...
# kind of a hack... :-/
class SingleEntryToken(Token):
    def __init__(self, cache_obj):
        self.cache_obj = cache_obj
        super(SingleEntryToken, self).__init__(name=cache_obj.name + "FAKE",
                                               provided_params=range(len(cache_obj.params)),
                                               cache=cache_obj.cache)

    def delete_filt(self, filt, send_signal=True):
        """ Given a filtered set of arguments, deletes things. """
        # filt is an arg_list
        self.cache_obj.delete(filt)
    delete_filt.alters_data = True

# FIXME: THIS IS CURRENTLY BROKEN
# ArgCache just uses cached value as-is before doing anything...
class ExternalToken(Token):
    """ A token that proves not only you occurred after a specified event, but
    that you were consistent with some other external information. For
    instance, a hash of a function signature. The external factor can be
    changed at runtime, but that's kind of silly... you could just delete all
    values of the parent cache. The intent is for dependencies on load-time
    state."""

    def __init__(self, external, *args, **kwargs):
        super(ExternalToken, self).__init__(*args, **kwargs)
        self.external = external

    def value_key(self, key):
        """ Combines the token value with the external factor. """
        return hash( (self.external, super(ExternalToken, self).value_key(key)) )
