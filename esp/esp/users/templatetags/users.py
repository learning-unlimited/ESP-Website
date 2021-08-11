from django import template

from esp.program.models import Program
from esp.users.models import Permission

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
