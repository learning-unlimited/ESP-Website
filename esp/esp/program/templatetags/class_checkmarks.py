
from django import template


register = template.Library()


@register.filter
def is_checked(klass, checkitem):
    # This function will be called repeatedly; let Django cache checklist_progress:
    
    for i in klass.checklist_progress_all_cached():
        if i.id == checkitem.id:
            return True

    return False
#    return len(klass.checklist_progress.filter(id = checkitem.id).values('id')[:1])
