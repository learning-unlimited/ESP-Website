from django import template
from esp.web.util.template import cache_inclusion_tag
from esp.cache.key_set import wildcard
from esp.program.models import Program, ClassSubject, ClassSection

register = template.Library()

@cache_inclusion_tag(register, 'inclusion/program/class_manage_row.html')
def render_class_row(klass):
    return {'cls': klass,
            'program': klass.parent_program}           
render_class_row.cached_function.depend_on_row(ClassSubject, lambda cls: {'klass': cls})
render_class_row.cached_function.depend_on_row(ClassSection, lambda sec: {'klass': sec.parent_class})
render_class_row.cached_function.depend_on_cache(ClassSubject.title, lambda self=wildcard, **kwargs: {'klass': self})
render_class_row.cached_function.depend_on_cache(ClassSubject.teachers, lambda self=wildcard, **kwargs: {'klass': self})
