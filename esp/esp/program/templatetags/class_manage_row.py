from django import template
from esp.web.util.template import cache_inclusion_tag

register = template.Library()

@cache_inclusion_tag(register, 'inclusion/program/class_manage_row.html')
def render_class_row(klass, program):
    return {'cls': klass,
            'program': program}
