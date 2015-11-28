from django import template
from django.template.loader import render_to_string

from argcache import cache_function, wildcard
from esp.utils.cache_inclusion_tag import cache_inclusion_tag
from esp.qsdmedia.models import Media as QSDMedia
from esp.program.models import ClassSubject, ClassSection, StudentAppQuestion
from esp.tagdict.models import Tag

register = template.Library()


@cache_inclusion_tag(register, 'inclusion/program/class_catalog_core.html')
def render_class_core(cls):
    prog = cls.parent_program
    scrmi = prog.getModuleExtension('StudentClassRegModuleInfo')
    colorstring = prog.getColor()
    if colorstring is not None:
        colorstring = ' background-color:#' + colorstring + ';'

    # Allow tag configuration of whether class descriptions get collapsed
    # when the class is full (default: yes)
    collapse_full = Tag.getBooleanTag('collapse_full_classes', prog, True)

    return {'class': cls,
            'collapse_full': collapse_full,
            'colorstring': colorstring,
            'show_enrollment': scrmi.visible_enrollments,
            'show_emailcodes': scrmi.show_emailcodes}
render_class_core.cached_function.depend_on_row(ClassSubject, lambda cls: {'cls': cls})
render_class_core.cached_function.depend_on_row(ClassSection, lambda sec: {'cls': sec.parent_class})
render_class_core.cached_function.depend_on_cache(ClassSection.num_students, lambda self=wildcard, **kwargs: {'cls': self.parent_class})
render_class_core.cached_function.depend_on_m2m(ClassSection, 'meeting_times', lambda sec, ts: {'cls': sec.parent_class})
render_class_core.cached_function.depend_on_row(StudentAppQuestion, lambda ques: {'cls': ques.subject})
render_class_core.cached_function.depend_on_m2m(ClassSubject, 'teachers', lambda cls, user: {'cls': cls})
render_class_core.cached_function.depend_on_row(QSDMedia, lambda media: {'cls': media.owner}, lambda media: isinstance(media.owner, ClassSubject))
render_class_core.cached_function.depend_on_model('modules.StudentClassRegModuleInfo')
render_class_core.cached_function.depend_on_model('modules.ClassRegModuleInfo')
render_class_core.cached_function.depend_on_model('tagdict.Tag')


@cache_inclusion_tag(register, 'inclusion/program/class_catalog.html')
def render_class(cls, user=None, prereg_url=None, filter=False, timeslot=None):
    return render_class_helper(cls, user, prereg_url, filter, timeslot)
render_class.cached_function.depend_on_cache(render_class_core.cached_function, lambda cls=wildcard, **kwargs: {'cls': cls})
render_class.cached_function.get_or_create_token(('cls',))
# We need to depend on not only the user's StudentRegistrations for this
# section, but in fact on their StudentRegistrations for all sections, because
# of things like lunch constraints -- a change made in another block could
# affect whether you can add a class in this one.  So we depend on all SRs for
# this user.  This only applies to tags that can depend on a user.
render_class.cached_function.depend_on_row('program.StudentRegistration', lambda reg: {'user': reg.user})
render_class.cached_function.get_or_create_token(('user',))


@cache_function
def render_class_direct(cls):
    return render_to_string('inclusion/program/class_catalog.html', render_class_helper(cls))
render_class_direct.depend_on_cache(render_class_core.cached_function, lambda cls=wildcard, **kwargs: {'cls': cls})


def render_class_helper(cls, user=None, filter=False, timeslot=None):
    scrmi = cls.parent_program.getModuleExtension('StudentClassRegModuleInfo')
    crmi = cls.parent_program.getModuleExtension('ClassRegModuleInfo')

    if timeslot:
        section = cls.get_section(timeslot=timeslot)
    else:
        section = None

    if (crmi.open_class_registration and
            cls.category == cls.parent_program.open_class_category):
        prereg_url = None
    else:
        prereg_url = cls.parent_program.get_learn_url() + 'addclass'

    if user and prereg_url and timeslot:
        errormsg = cls.cannotAdd(user, which_section=section)
    else:
        errormsg = None

    show_class = (not filter) or (not errormsg)

    return {'class':      cls,
            'section':    section,
            'user':       user,
            'prereg_url': prereg_url,
            'errormsg':   errormsg,
            'temp_full_message': scrmi.temporarily_full_text,
            'show_class': show_class}


@cache_inclusion_tag(register, 'inclusion/program/class_catalog_preview.html')
def render_class_preview(cls):
    return {'class': cls}
render_class_preview.cached_function.depend_on_row(ClassSubject, lambda cls: {'cls': cls})
render_class_preview.cached_function.depend_on_m2m(ClassSubject, 'teachers', lambda cls, user: {'cls': cls})


@cache_inclusion_tag(register, 'inclusion/program/class_catalog_row.html')
def render_class_row(cls):
    return {'class': cls}
render_class_row.cached_function.depend_on_row(ClassSubject, lambda cls: {'cls': cls})
render_class_row.cached_function.depend_on_row(ClassSection, lambda sec: {'cls': sec.parent_class})
render_class_row.cached_function.depend_on_cache(ClassSection.num_students, lambda self=wildcard, **kwargs: {'cls': self.parent_class})
render_class_row.cached_function.depend_on_m2m(ClassSubject, 'teachers', lambda cls, user: {'cls': cls})
render_class_row.cached_function.depend_on_m2m(ClassSection, 'meeting_times', lambda sec, ts: {'cls': sec.parent_class})
render_class_row.cached_function.depend_on_model('modules.StudentClassRegModuleInfo')
render_class_row.cached_function.depend_on_row('resources.ResourceAssignment', lambda ra: {'cls': ra.target.parent_class})
