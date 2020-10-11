from django import template
from django.conf import settings

from argcache import wildcard
from esp.utils.cache_inclusion_tag import cache_inclusion_tag
from esp.program.models import ClassSubject, ClassSection
from esp.tagdict.models import Tag

register = template.Library()


@cache_inclusion_tag(register, 'inclusion/program/class_teacher_list_row.html')
def render_class_teacher_list_row(cls, can_req_cancel, survey_results):
    """Render a class for the teacher list of classes in teacherreg."""
    return {'cls': cls,
            'program': cls.parent_program,
            'crmi': cls.parent_program.classregmoduleinfo,
            'can_req_cancel': can_req_cancel,
            'survey_results': survey_results,
            'friendly_times_with_date': Tag.getBooleanTag(
                'friendly_times_with_date', cls.parent_program),
            'email_host_sender': settings.EMAIL_HOST_SENDER
            }
render_class_teacher_list_row.cached_function.depend_on_row(ClassSubject, lambda cls: {'cls': cls})
render_class_teacher_list_row.cached_function.depend_on_row(ClassSection, lambda sec: {'cls': sec.parent_class})
render_class_teacher_list_row.cached_function.depend_on_cache(ClassSubject.get_teachers, lambda self=wildcard, **kwargs: {'cls': self})
render_class_teacher_list_row.cached_function.depend_on_row('resources.ResourceAssignment', lambda ra: {'cls': ra.target.parent_class})


@cache_inclusion_tag(register, 'inclusion/program/class_copy_row.html')
def render_class_copy_row(cls):
    """Render a class for the list of classes that can be copied in teacherreg.

    Similar to render_class_teacher_list_row, but with a few differences.
    """
    return {'cls': cls,
            'program': cls.parent_program,
            'crmi': cls.parent_program.classregmoduleinfo}
render_class_copy_row.cached_function.depend_on_cache(
    render_class_teacher_list_row.cached_function,
    lambda cls=wildcard, **kwargs: {'cls': cls})
