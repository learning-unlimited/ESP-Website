from django.conf import settings

if getattr(settings, "WARN_ON_LAZY_QUERIES", False):

    from django.db.models.fields.related import ReverseSingleRelatedObjectDescriptor

    __orig_get = ReverseSingleRelatedObjectDescriptor.__get__

    def get_notify(self, instance, instance_type=None):
        if instance is not None and not hasattr(instance, self.field.get_cache_name()):
            print "Deferred lookup of", type(instance), "(type", type, ")"
        return __orig_get(self, instance, instance_type)


    ReverseSingleRelatedObjectDescriptor.__get__ = get_notify

