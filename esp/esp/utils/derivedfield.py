#!/usr/bin/python
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2010 by the individual contributors
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

import sys

from south.modelsinspector import introspector

def DerivedField(FieldCls, getter_fn):
    """
    Returns a Django Model Field that is derived, ie., that is
    automatically calculated based on the values of other fields.

    The intent of this field is to push caching out to the database:
    It is sometimes useful to run queries that filter against calculated
    fields or fields that can only be found across an expensive series
    of joins.  For example, sorting classes by their starting times
    or by the number of students in them.  These values can often be
    calculated in SQL by a crazy SQL query; but such queries can be quite
    expensive.  So, let's create a field that stores these calculated
    values, and that automatically recalculates them when they
    change.

    DerivedField() is a field *generator*, not a field itself.
    Its usage is as follows.  Let's say I have a model with an IntegerField:

    #>>> from django.db import models
    #>>> class MyModel(models.Model):
    #>>>     mySum = models.IntegerField(null=False, default=0)

    To make this into a DerivedField, I'd need to do the following:

    #>>> from esp.utils.derivedfield import DerivedField
    #>>> MyNewDerivedFieldType = DerivedField(models.IntegerField, counter_fn)
    #>>> class MyModel(models.Model):
    #>>>     mySum = MyNewDerivedFieldType(null=False, default=0)

    (Or, alternatively,)

    #>>> class MyModel(models.Model):
    #>>>     mySum = DerivedField(models.IntegerField, counter_fn)(null=False, default=0)

    Now, note that I specified an argument "counter_fn".  counter_fn must be
    a function that is cached using the caching API (esp.cache.argcache).
    This code is an extension of the caching API: When that API flushes the
    cache in memcached, this code catches that event and also updates the value
    stored in the database.  So, for example:

    #>>> class Frob(models.Model):
    #>>>     " Example model that we might want to count "
    #>>>     myModelFk = models.ForeignKey(MyModel)
    #>>>
    #>>> from esp.cache import cache_function
    #>>> @cache_function 
    #>>> def counter_fn(self):
    #>>>     return self.frob_set.count()
    #>>> counter_fn.depend_on_row(lambda:Frob, lambda frob: {'self': frob.myModelFk})

    Note that counter_fn() (or getter_fn(), the generic name of this thing)
    must take at most one argument, and that one argument must be
    an instance of the same model that this field is a field on.
    So in the above example, 'self' must always be an instance of MyModel.
    This constraint may be loosened in the future.

    Be careful to make the cache as granular as you possibly can!
    If the above example were to do, for example,

    #>>> counter_fn.depend_on_model(lambda:Frob)

    instead of .depend_on_row(), then every time the Frob table got updated,
    the cache for every row in the MyModel table gets flushed, and so
    counter_fn() *immediately gets called once for every row in MyModel*
    to regenerate the cache!  Unless MyModel is quite tiny, this is going
    to be very expensive.
    """
    assert callable(getter_fn) and hasattr(getter_fn, 'connect'), "'getter_fn' must be a Python function that's cached by the caching API's 'cache_function' decorator"

    class NewCls(FieldCls):
        """ Wrapper class for the %s model-field, giving a field that is automatically updated """ % FieldCls.__name__
        def __init__(self, *args, **kwargs):
            super(FieldCls, self).__init__(*args, **kwargs)

            ## Lock to prevent reentrancy on our handler function
            self._derived_reentrant_lock = False

            def handler(key_set, **kwargs):
                assert len(key_set) <= 1, "Error, getter function seems to be cached against more than one argument: %s" % (repr(key_set))

                assert (not self._derived_reentrant_lock), "Trigger cycle detected (A updates B updates C updates A updates B updates ...)!  Aborting to prevent infinite loop."
                self._derived_reentrant_lock = True

                try:
                    if len(key_set) == 0:
                        ## Ok then, the whole cache got dumped; full reset time!
                        for elt in self.model.objects.all():
                            new_val = getter_fn(elt)
                            if new_val != getattr(elt, self.name):
                                setattr(elt, self.name, new_val)
                                elt.save()
                
                    else:
                        item = key_set.values()[0]
                        ## TODO: The following test doesn't actually work; self.model claims to be an instance of ModelBase, even though we seem to be able to query it
                        #assert type(item) == type(self.model), "Error, passed an item of type %s into a cache-function that only accepts items of type %s" % (str(type(item)), str(type(self.model)))
                        row = self.model.objects.get(id=key_set.values()[0].id)  ## Get a new instance of this model, so that we don't have to worry about unsaved data in other fields
                        new_val = getter_fn(row)
                        if new_val != getattr(row, self.name):
                            setattr(row, self.name, new_val)
                            row.save()
                except Exception, e:
                    raise e
                finally:  ## Put the unlock in a 'finally' block so that it always happens
                    self._derived_reentrant_lock = False
            getter_fn.connect(handler)

        def south_field_triple(self, ):
            # XXX: Uhhh... Such a hack... FIIK this really works
            field_class = FieldCls.__module__ + "." + self.get_internal_type()
            args, kwargs = introspector(self)
            return (field_class, args, kwargs, )

    return NewCls
