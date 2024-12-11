from __future__ import absolute_import
from django import template
from django.conf import settings

from argcache import wildcard
from esp.utils.cache_inclusion_tag import cache_inclusion_tag
from esp.program.models import ClassSubject, ClassSection
from esp.tagdict.models import Tag

register = template.Library()

@cache_inclusion_tag(register, 'inclusion/program/section_moderator_list_row.html')
def render_section_moderator_list_row(sec):
    """Render a section for the moderator list of classes in teacherreg."""
    prog = sec.parent_class.parent_program
    return {'sec': sec,
            'program': prog,
            'friendly_times_with_date': Tag.getBooleanTag(
                'friendly_times_with_date', prog),
            'email_host_sender': settings.EMAIL_HOST_SENDER
            }
render_section_moderator_list_row.cached_function.depend_on_model('program.ClassSubject')
render_section_moderator_list_row.cached_function.depend_on_row(ClassSection, lambda sec: {'sec': sec})
render_section_moderator_list_row.cached_function.depend_on_cache(ClassSubject.get_teachers, lambda self=wildcard, **kwargs: {'sec': self})
render_section_moderator_list_row.cached_function.depend_on_row('resources.ResourceAssignment', lambda ra: {'sec': ra.target})
