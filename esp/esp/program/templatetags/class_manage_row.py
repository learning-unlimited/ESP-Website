from django import template
from esp.web.util.template import cache_inclusion_tag

register = template.Library()


def cache_key(klass, program):
    return "CLASS_MANAGE_ROW__%d" % klass.id


@cache_inclusion_tag(register, 'inclusion/program/class_manage_row.html',  cache_key_func=cache_key)
def render_class_row(klass, program):
    return {'cls': klass,
            'program': program}
