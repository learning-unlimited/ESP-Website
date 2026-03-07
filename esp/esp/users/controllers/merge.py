import logging

from django.db import transaction
from django.db.utils import IntegrityError

logger = logging.getLogger(__name__)

from esp.users.models import UserForwarder

__all__ = ['get_related', 'merge', 'merge_users']

#####################
# Internal use only #
#####################

def _populate_related(target, related_list, many_to_many):
    """Populate a list of related objects in a palatable format."""
    ans = []
    for related in related_list:
        name_out = related.get_accessor_name()
        name_in = related.field.name
        objects = getattr(target, name_out, None)
        if objects is None:
            continue
        for obj in objects.all():
            ans.append((obj, name_in, many_to_many))
    return ans

def _get_simply_related(target):
    """Gets objects related to 'target' through anything but many-to-many."""
    objects = [f for f in target._meta.get_fields() if (f.one_to_many or f.one_to_one) and f.auto_created and not f.concrete]
    return _populate_related(target, objects, False)

def _get_m2m_related(target):
    """Gets objects related to 'target' through a many-to-many."""
    objects = [f for f in target._meta.get_fields(include_hidden=True) if f.many_to_many and f.auto_created]
    return _populate_related(target, objects, True)


################################
# Potentially useful elsewhere #
################################

def get_related(target):
    """
    Gets objects related to 'target'.

    Returns a list of tuples (object, field_name, many_to_many).
    e.g. (<ClassSubject>, 'meeting_times', True)

    """
    return _get_simply_related(target) + _get_m2m_related(target)

def merge(absorber, absorbee):
    """Transfers everything from absorbee to absorber."""
    for obj, name, m2m in get_related(absorbee):
        try:
            with transaction.atomic():
                if m2m:
                    rel = getattr(obj, name)
                    if rel.through._meta.auto_created:
                        # For symmetric relations (e.g., "friends"), skip
                        # self-referential additions that would occur when the
                        # related object is the absorber itself.
                        if obj.pk == absorber.pk:
                            rel.remove(absorbee)
                        else:
                            rel.remove(absorbee)
                            rel.add(absorber)
                else:
                    setattr(obj, name, absorber)
                    obj.save()
        except IntegrityError:
            logger.warning(
                "IntegrityError while merging %s %s.%s from user %s to %s; "
                "skipping (likely duplicate constraint)",
                obj.__class__.__name__, obj.pk, name, absorbee.pk, absorber.pk
            )
    # Also transfer forward m2m relations (including symmetric).
    for field in absorber._meta.local_many_to_many:
        absorbee_related = getattr(absorbee, field.attname)
        absorber_related = getattr(absorber, field.attname)
        related_objects = absorbee_related.all()
        # For symmetric self-referential fields, exclude the absorber
        # to prevent a user being related to themselves after merge.
        if field.related_model == type(absorber):
            related_objects = related_objects.exclude(pk=absorber.pk)
        absorber_related.add(*related_objects)


#########################
# Usable from the shell #
#########################

@transaction.atomic
def merge_users(absorber, absorbee, forward=True, deactivate=False):
    """
    Merge two accounts, transferring everything from absorbee to abosorber.

    Options:
        forward: Set up login forwarding from absorbee to absorber
        deactivate: Deactivate the absorbee

    """
    merge(absorber, absorbee)
    # Set up forwarding
    if forward:
        UserForwarder.forward(absorbee, absorber)
    # Deactivate the absorbed account.
    if deactivate:
        absorbee.is_active = False
        absorbee.save()
