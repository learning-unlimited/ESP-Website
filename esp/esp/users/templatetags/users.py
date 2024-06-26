from __future__ import absolute_import
from django import template

from esp.program.models import Program
from esp.users.models import Permission, Record, RecordType

register = template.Library()

@register.filter
def getGradeForProg(user, prog_id):
    """Return the grade of the user for the specified program id."""
    if prog_id is None:
        return user.getGrade()
    else:
        return user.getGrade(Program.objects.get(id=int(prog_id)))

@register.filter
def perm_nice_name(perm):
    """Return the nice name of the permission type."""
    return Permission.nice_name_lookup(perm)

@register.filter
def remove_from_qs(queryset, user):
    """Remove a given user from a Queryset of users."""
    return queryset.exclude(id=user.id)

@register.simple_tag
def checkRecordForProgram(user, record, program):
    """Return whether the specified record exists for the specified user for specified program."""
    return Record.user_completed(user, record, program)

@register.filter
def getRecordDescription(record):
    """ Return the full description for a record """
    event_dict = dict(RecordType.desc())
    return event_dict[record]
