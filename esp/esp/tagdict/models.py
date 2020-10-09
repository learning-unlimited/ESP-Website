import logging
logger = logging.getLogger(__name__)

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from argcache import cache_function

from esp.tagdict import all_global_tags, all_program_tags

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
    target = GenericForeignKey(ct_field='content_type', fk_field='object_id')
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

    @classmethod
    def getTag(cls, key, target=None, default=None):
        """
        Will pull the default from __init__.py unless the default argument is specified.
        """
        if key not in all_global_tags:
            logger.warning("Tag %s not in list of global tags", key)
        elif all_global_tags[key].get('is_boolean', False):
            logger.warning("Tag %s should be used with getBooleanTag", key)

        if target is not None:
            logger.warning("getTag() called for key %s with specific target; consider using getProgramTag()",
                           key)

        result = cls._getTag(key, target=target)
        if result is None: #See the comment in getProgramTag for why we're using None rather than passing the default through.
            if default is not None:
                result = default
            else:
                if key in all_program_tags:
                    result = all_program_tags[key].get('default')
                elif key in all_global_tags:
                    result = all_global_tags[key].get('default')

        if isinstance(result, basestring) and (result.lower() == "false" or
                                               result.lower() == "true"):
            logger.warning("Tag %s set to boolean value; consider using getBooleanTag()",
                           key)
        return result

    @cache_function
    def _getTag(cls, key, default=None, target=None):
        """
        Given a key (as a slug) and a target row from any database table,
        return the corresponding value as a string,
        or the value specified by the 'default' argument if no such value exists.
        """
        if default is not None and not isinstance(default, basestring):
            logger.warning("_getTag() called with non-string default for key %s",
                           key)

        try:
            if target != None:
                ct = ContentType.objects.get_for_model(target)
                return cls.objects.get(key=key, content_type=ct, object_id=target.id).value
            else:
                return cls.objects.get(key=key, content_type__isnull=True, object_id__isnull=True).value
        except cls.DoesNotExist:
            return default
    _getTag.depend_on_row('tagdict.Tag', lambda tag: {'key': tag.key, 'target': tag.target})
    _getTag = classmethod(_getTag)

    @classmethod
    def getProgramTag(cls, key, program=None, default=None, boolean=False):
        """
        Given a key and program, return the corresponding value as string.
        If the program does not have the tag set, return the global value.
        Will pull the default from __init__.py unless the default argument is specified.
        """
        if key not in all_program_tags:
            logger.warning("Tag %s not in list of program tags", key)
        elif all_program_tags[key].get('is_boolean', False) and not boolean:
            logger.warning("Tag %s should be used with getBooleanTag", key)

        res = None
        # We use None, rather than default, as our default so that we hit the
        # same _getTag cache independently of the default.  Since _getTag should
        # always return either a string if a tag was found, and None otherwise,
        # this works.
        if program is not None:
            res = cls._getTag(key, target=program)
        if res is None:
            res = cls._getTag(key)
        if res is None:
            if default is not None:
                res = default
            else:
                if key in all_program_tags:
                    res = all_program_tags[key].get('default')
                elif key in all_global_tags:
                    res = all_global_tags[key].get('default')
        if (not boolean) and isinstance(res, basestring) and \
           (res.lower() == "false" or res.lower() == "true"):
            logger.warning("Tag %s set to boolean value; consider using getBooleanTag()",
                           key)
        return res

    @classmethod
    def getBooleanTag(cls, key, program=None, default=None):
        """
        A variant of getProgramTag that returns boolean values.
        The default argument should also be boolean.
        Will pull the default from __init__.py unless the default argument is specified.
        """
        if (key not in all_program_tags or not all_program_tags[key].get('is_boolean', False)) \
           and (key not in all_global_tags or not all_global_tags[key].get('is_boolean', False)):
            logger.warning("Tag %s not in list of boolean tags", key)
        if program:
            tag_val = Tag.getProgramTag(key, program, boolean=True, default=default)
        else:
            tag_val = Tag._getTag(key)
        if tag_val is None: #See the comment in getProgramTag for why we're using None rather than passing the default through.
            if default is not None:
                return default
            else:
                if key in all_program_tags:
                    return all_program_tags[key].get('default')
                elif key in all_global_tags:
                    return all_global_tags[key].get('default')
                else:
                    return None
        elif isinstance(tag_val, bool):
            return tag_val
        elif tag_val.strip().lower() == 'true' or tag_val.strip() == '1':
            return True
        else:
            return False

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
            tag, created = cls.objects.get_or_create(key=key, content_type=None, object_id=None)

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
