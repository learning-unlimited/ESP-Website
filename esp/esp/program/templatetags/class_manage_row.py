from django import template


register = template.Library()



@register.inclusion_tag('inclusion/program/class_manage_row.html')
def render_class_row(klass, program):
    return {'cls': klass,
            'program': program}
