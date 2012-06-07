from django import template
from esp.web.util.template import cache_inclusion_tag
from esp.cache.key_set import wildcard
from esp.program.models import Program, ClassSubject, ClassSection
from esp.tagdict.models import Tag

register = template.Library()

@cache_inclusion_tag(register, 'inclusion/program/class_manage_row.html')
def render_class_manage_row(klass):
    return {'cls': klass,
            'program': klass.parent_program}           
render_class_manage_row.cached_function.depend_on_row(ClassSubject, lambda cls: {'klass': cls})
render_class_manage_row.cached_function.depend_on_row(ClassSection, lambda sec: {'klass': sec.parent_class})
#render_class_manage_row.cached_function.depend_on_cache(ClassSubject.title, lambda self=wildcard, **kwargs: {'klass': self})
#render_class_manage_row.cached_function.depend_on_m2m(lambda: ClassSubject, 'teachers',lambda sec,ev: {'self':sec}) #depend_on_cache(ClassSubject.teachers, lambda self=wildcard, **kwargs: {'klass': self})


@cache_inclusion_tag(register, 'inclusion/program/class_teacher_list_row.html')
def render_class_teacher_list_row(klass):
    return {'cls': klass,
            'program': klass.parent_program,
            'teacherclsmodule': klass.parent_program.getModuleExtension('ClassRegModuleInfo'),
            'friendly_times_with_date': (Tag.getProgramTag(key='friendly_times_with_date', program=klass.parent_program, default=False) == "True")}
render_class_teacher_list_row.cached_function.depend_on_row(ClassSubject, lambda cls: {'klass': cls})
render_class_teacher_list_row.cached_function.depend_on_row(ClassSection, lambda sec: {'klass': sec.parent_class})
#render_class_teacher_list_row.cached_function.depend_on_cache(ClassSubject.title, lambda self=wildcard, **kwargs: {'klass': self})
#render_class_teacher_list_row.cached_function.depend_on_m2m(lambda: ClassSubject, 'teachers',lambda sec,ev: {'self':sec}) #depend_on_cache(ClassSubject.teachers, lambda self=wildcard, **kwargs: {'klass': self})


@cache_inclusion_tag(register, 'inclusion/program/class_copy_row.html')
def render_class_copy_row(klass):
    return {'cls': klass,
            'program': klass.parent_program,
            'teacherclsmodule': klass.parent_program.getModuleExtension('ClassRegModuleInfo')}          
render_class_teacher_list_row.cached_function.depend_on_row(ClassSubject, lambda cls: {'klass': cls})
render_class_teacher_list_row.cached_function.depend_on_row(ClassSection, lambda sec: {'klass': sec.parent_class})
#render_class_teacher_list_row.cached_function.depend_on_cache(ClassSubject.title, lambda self=wildcard, **kwargs: {'klass': self})
#render_class_teacher_list_row.cached_function.depend_on_m2m(lambda: ClassSubject, 'teachers',lambda sec,ev: {'self':sec}) #depend_on_cache(ClassSubject.teachers, lambda self=wildcard, **kwargs: {'klass': self})
