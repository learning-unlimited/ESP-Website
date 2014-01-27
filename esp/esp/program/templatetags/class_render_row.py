from django import template
from django.conf import settings
from esp.web.util.template import cache_inclusion_tag
from esp.cache.key_set import wildcard
from esp.program.models import Program, ClassSubject, ClassSection
from esp.tagdict.models import Tag
from esp.middleware.threadlocalrequest import AutoRequestContext

register = template.Library()

@cache_inclusion_tag(register, 'inclusion/program/class_manage_row.html')
def render_class_manage_row(klass):
    return {'cls': klass,
            'program': klass.parent_program}           
render_class_manage_row.cached_function.depend_on_row(ClassSubject, lambda cls: {'klass': cls})
render_class_manage_row.cached_function.depend_on_row(ClassSection, lambda sec: {'klass': sec.parent_class})
render_class_manage_row.cached_function.depend_on_cache(ClassSubject.get_teachers, lambda self=wildcard, **kwargs: {'klass': self})


# Dubious that this is the best way to fix things.
# The symptom, so that I don't forget:
# The "E-mail students" buttons in the class list in teacherreg
# doesn't include a domain in the e-mail address. -ageng 2012-10-03
# Clobberable. I saw this fix in main a while ago. -ageng 2013-08-12
@cache_inclusion_tag(register, 'inclusion/program/class_teacher_list_row.html', context_class=AutoRequestContext)
def render_class_teacher_list_row(klass):
    return {'cls': klass,
            'program': klass.parent_program,
            'teacherclsmodule': klass.parent_program.getModuleExtension('ClassRegModuleInfo'),
            'friendly_times_with_date': (Tag.getProgramTag(key='friendly_times_with_date', program=klass.parent_program, default=False) == "True"),
            'email_host': settings.EMAIL_HOST
            }
render_class_teacher_list_row.cached_function.depend_on_row(ClassSubject, lambda cls: {'klass': cls})
render_class_teacher_list_row.cached_function.depend_on_row(ClassSection, lambda sec: {'klass': sec.parent_class})
render_class_teacher_list_row.cached_function.depend_on_cache(ClassSubject.get_teachers, lambda self=wildcard, **kwargs: {'klass': self})


@cache_inclusion_tag(register, 'inclusion/program/class_copy_row.html')
def render_class_copy_row(klass):
    return {'cls': klass,
            'program': klass.parent_program,
            'teacherclsmodule': klass.parent_program.getModuleExtension('ClassRegModuleInfo')}          
# These should possibly say render_class_copy_row
# but I'm too lazy to figure it out right now. -ageng 2012-10-03
render_class_teacher_list_row.cached_function.depend_on_row(ClassSubject, lambda cls: {'klass': cls})
render_class_teacher_list_row.cached_function.depend_on_row(ClassSection, lambda sec: {'klass': sec.parent_class})
render_class_copy_row.cached_function.depend_on_cache(ClassSubject.get_teachers, lambda self=wildcard, **kwargs: {'klass': self})
