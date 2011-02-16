""" Lame hack to ensure all caches are inserted. """

#   Attempt to make newer versions of Django properly realize that this module
#   does not have models.
__path__ = ''

# This is in a separate app because example caches may be in unit tests and
# whatnot for esp.cache. This is probably fine if done properly, but I'd rather
# not have to think about that.

import sys
from django.conf import settings
from esp.cache.registry import _finalize_caches, _lock_caches
from esp.cache.signals import m2m_removed, m2m_added

# Make sure everything's already imported

# Import views files from INSTALLED_APPS
for app_name in settings.INSTALLED_APPS:
    if app_name != 'esp.cache_loader':
        __import__(app_name, {}, {}, ['models'])
    # HACK: Duplicate esp.foo in sys.modules as foo.
    # This lets console users type "import program.models"
    # As shorthand for "import esp.program.models".
    # In the code you should of course still write out the "esp."
    if app_name.startswith('esp.'):
        for key, value in sys.modules.items():
           if key.startswith(app_name):
               sys.modules[key[4:]] = value


#   Make sure all cached inclusion tags are registered
from esp.utils.inclusion_tags import *

# import esp.cache.test

# Fix up the queued events
_finalize_caches()
_lock_caches()


# HACK!!! Monkey-patch M2M stuff...
# LATER: Go yell at Django devs to integrate patch #5390

# XXX: This one will need a unit test... REALLY

from django.db.models.fields import related
old_one = related.create_many_related_manager
def new_create_many_related_manager(*args, **kwargs):
    OldClass = old_one(*args, **kwargs)

    # FIXME: Does not filter list of objs for unnecessary stuff
    # probably should just wait for Django to add the signal
    if hasattr(OldClass, 'add'):
        old_add = OldClass.add
        def new_add(self, *objs):
            # Bah, would probably be more efficient if we require signal handlers to handle ids everywhere
            actual_objs = [obj if isinstance(obj, self.model) else self.model.objects.get(id=obj) for obj in objs]
            for obj in actual_objs:
                m2m_added.send(sender=self.instance.__class__, instance=self.instance, object=obj, field=self.field_name)
                m2m_added.send(sender=self.model, instance=obj, object=self.instance, field=self.rev_field_name)
            ans = old_add(self, *objs)
            return ans
        new_add.alters_data = True
        OldClass.add = new_add

    # FIXME: Does not filter list of objs for unnecessary stuff
    # probably should just wait for Django to add the signal
    if hasattr(OldClass, 'remove'):
        old_remove = OldClass.remove
        def new_remove(self, *objs):
            # Bah, would probably be more efficient if we require signal handlers to handle ids everywhere
            actual_objs = [obj if isinstance(obj, self.model) else self.model.objects.get(id=obj) for obj in objs]
            for obj in actual_objs:
                m2m_removed.send(sender=self.instance.__class__, instance=self.instance, object=obj, field=self.field_name)
                m2m_removed.send(sender=self.model, instance=obj, object=self.instance, field=self.rev_field_name)
            ans = old_remove(self, *objs)
            return ans
        new_remove.alters_data = True
        OldClass.remove = new_remove

    if hasattr(OldClass, 'clear'):
        old_clear = OldClass.clear
        def new_clear(self, *objs):
            actual_objs = [obj if isinstance(obj, self.model) else self.model.objects.get(id=obj) for obj in objs]
            for obj in self.all():
                m2m_removed.send(sender=self.instance.__class__, instance=self.instance, object=obj, field=self.field_name)
                m2m_removed.send(sender=self.model, instance=obj, object=self.instance, field=self.rev_field_name)
            ans = old_clear(self, *objs)
            return ans
        new_clear.alters_data = True
        OldClass.clear = new_clear


    return OldClass
related.create_many_related_manager = new_create_many_related_manager

old_get = related.ManyRelatedObjectsDescriptor.__get__
def new__get__(self, *args, **kwargs):
    manager = old_get(self, *args, **kwargs)
    manager.field_name = self.related.get_accessor_name()
    manager.rev_field_name = self.related.field.name
    return manager
related.ManyRelatedObjectsDescriptor.__get__ = new__get__
old_rev_get = related.ReverseManyRelatedObjectsDescriptor.__get__
def new__rev_get__(self, instance, instance_type=None):
    manager = old_rev_get(self, instance, instance_type)
    manager.field_name = self.field.name

    # BAH...
    rel_obj = related.RelatedObject(self.field.rel.to, instance.__class__, self.field)
    manager.rev_field_name = rel_obj.get_accessor_name()

    return manager
related.ReverseManyRelatedObjectsDescriptor.__get__ = new__rev_get__
