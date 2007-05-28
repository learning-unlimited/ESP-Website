
from django import template


register = template.Library()


@register.filter
def is_checked(klass, checkitem):
    return len(klass.checklist_progress.filter(id = checkitem.id).values('id')[:1])
