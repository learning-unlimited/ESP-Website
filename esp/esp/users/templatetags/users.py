from django import template

from esp.program.models import Program

register = template.Library()

@register.filter
def getGradeForProg(user, prog_id):
    """Return the grade of the user for the specified program id."""
    if prog_id is None:
        return user.getGrade()
    else:
        return user.getGrade(Program.objects.get(id=int(prog_id)))
