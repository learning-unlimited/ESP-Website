from django.db import transaction
from django.db.utils import IntegrityError

from esp.users.models import ESPUser, UserForwarder

__all__ = ['get_related', 'merge', 'trim_userbits', 'merge_users']

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
    return _populate_related(target, target._meta.get_all_related_objects(), False)

def _get_m2m_related(target):
    """Gets objects related to 'target' through a many-to-many."""
    return _populate_related(target, target._meta.get_all_related_many_to_many_objects(), True)


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
        # I could probably be smarter about transaction handling.
        # Ideally, I'd check for uniqueness constraints *before* saving.
        # Then I wouldn't have to do any transaction stuff here.
        transaction.enter_transaction_management()
        try:
            if m2m:
                getattr(obj, name).remove(absorbee)
                getattr(obj, name).add(absorber)
                # No need to save(); remove and add implicitly do it.
            else:
                setattr(obj, name, absorber)
                obj.save()
        except IntegrityError:
            transaction.rollback()
        finally:
            transaction.commit()
        transaction.leave_transaction_management()

def trim_userbits(user):
    """Drop duplicate userbits from user."""
    deletion_queue = []
    for b in user.userbit_set.all():
        if b.id != user.userbit_set.filter(qsc=b.qsc, verb=b.verb).order_by('-enddate','startdate')[0].id:
            deletion_queue.append(b)
    for b in deletion_queue:
        b.delete()


#########################
# Usable from the shell #
#########################

def merge_users(absorber, absorbee, forward=True, deactivate=False, trim_bits=True):
    """
    Merge two accounts, transferring everything from absorbee to abosorber.

    Options:
        forward: Set up login forwarding from absorbee to absorber
        deactivate: Deactivate the absorbee
        trim_bits: Drop duplicate userbits from the absorber

    """
    merge(absorber, absorbee)
    # Set up forwarding
    if forward:
        UserForwarder.forward(absorbee, absorber)
    # Deactivate the absorbed account.
    if deactivate:
        absorbee.is_active = False
        absorbee.save()
    # Drop duplicate userbits from the absorbing account.
    # Unnecessary if you're enforcing a uniqueness constraint on userbits.
    if trim_bits:
        trim_userbits(absorber)
