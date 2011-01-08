from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from esp.cache import cache_function

# aseering 3/23/2010
# This model is based on the sample "TaggedItem" model from the Django
# documentation, as described at
# http://www.djangoproject.com/documentation/models/generic_relations/

class Tag(models.Model):
    """A tag on an item."""
    key = models.SlugField(db_index=True)
    value = models.TextField()

    ## Generic ForeignKey ##
    content_type = models.ForeignKey(ContentType, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    target = generic.GenericForeignKey(ct_field='content_type', fk_field='object_id')
    ## End Generic ForeignKey ##

    class Meta:
        ordering = ["key"]

        unique_together = (("key", "content_type", "object_id"),)
        # We really want to enforce that keys be unique if content_type
        # and object_id are both null.  However null's are special in SQL.
        # Django can't currently do this, so it's enforced by custom SQL.
        # TODO:  Write this custom SQL for backends other than PostgreSQL.

    def __unicode__(self):
        return "%s: %s (%s)" % (self.key, self.value, self.target)

    EMPTY_TAG = " "

    @cache_function
    def getTag(cls, key, target=None, default=None):
        """ 
        Given a key (as a slug) and a target row from any database table,
        return the corresponding value as a string,
        or the value specified by the 'default' argument if no such value exists.
        """
        try:
            if target != None:
                ct = ContentType.objects.get_for_model(target)
                return cls.objects.get(key=key, content_type=ct, object_id=target.id).value
            else:
                return cls.objects.get(key=key, content_type__isnull=True, object_id__isnull=True).value
        except cls.DoesNotExist:
            return default
    getTag.depend_on_row(lambda: Tag, lambda tag: {'key': tag.key, 'target': tag.target})
    getTag = classmethod(getTag)

    @classmethod
    def getProgramTag(cls, key, program=None, default=None, ):
        """
        Given a key and program, return the corresponding value as string.
        If the program does not have the tag set, return the global value.
        """
        res = None
        if program is not None:
            res = cls.getTag(key, target=program, default=None, )
        if res is None:
            res = cls.getTag(key, target=None, default=default, )
        return res
    
    @classmethod
    def setTag(cls, key, target=None, value=EMPTY_TAG):
        """
        Set a tag to a particular value.
        If the tag already exists and has a different value, change the value.

        If value is not specified, it is taken to be the magic value EMPTY_TAG, which is
        guaranteed to evaluate to True.  This allows
        "contentless" tags s.t. no data is stored, but "if getTag(foo)" will indicate
        that the tag has been set (or not).        
        """

        if target != None:
            ct = ContentType.objects.get_for_model(target)
            tag, created = cls.objects.get_or_create(key=key, content_type=ct, object_id=target.id)
        else:
            tag, created = cls.objects.get_or_create(key=key)

        if created or (tag.value != value):
            tag.value = value
            tag.save()

        return tag.value

    @classmethod
    def unSetTag(cls, key, target=None):
        """
        Delete the tag with the specified key and target, if one exists.
        Return the number of tags that were deleted; should always be one of "0" or "1",
        though if constraint-enforcing code hasn't been written for your database backend
        yet, this may not be enforced.
        (Note that this makes "if unSetTag(foo):" evaluate if the tag did exist.)
        """
        tag_counter = 0

        if target != None:
            ct = ContentType.objects.get_for_model(target)
            items = cls.objects.filter(key=key, content_type=ct, object_id=target.id)
        else:
            items = cls.objects.filter(key=key, content_type__isnull=True, object_id__isnull=True)

        for tag in items:
            tag.delete()
            tag_counter += 1

        return tag_counter
