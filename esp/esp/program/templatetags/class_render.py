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
    """Render non-user-specific parts of a class for the catalog."""
    prog = cls.parent_program
    scrmi = prog.studentclassregmoduleinfo
    colorstring = prog.getColor()
    if colorstring is not None:
        colorstring = ' background-color:#' + colorstring + ';'

    # Allow tag configuration of whether class descriptions get collapsed
    # when the class is full (default: yes)
    collapse_full = Tag.getBooleanTag('collapse_full_classes', prog)

    return {'class': cls,
            'collapse_full': collapse_full,
            'colorstring': colorstring,
            'show_enrollment': scrmi.visible_enrollments,
            'show_emailcodes': scrmi.show_emailcodes,
            'show_meeting_times': scrmi.visible_meeting_times}
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
def render_class(cls, user=None, filter=False, timeslot=None):
    """Render the entire class for the catalog, including user-specific parts.

    Calls render_class_core for non-user-specific parts.  Used in fillslot.
    """
    return _render_class_helper(cls, user, filter, timeslot)
render_class.cached_function.depend_on_cache(render_class_core.cached_function, lambda cls=wildcard, **kwargs: {'cls': cls})
render_class.cached_function.get_or_create_token(('cls',))
# We need to depend on not only the user's StudentRegistrations for this
# section, but in fact on their StudentRegistrations for all sections, because
# of things like lunch constraints -- a change made in another block could
# affect whether you can add a class in this one.  So we depend on all SRs for
# this user.  This only applies to tags that can depend on a user.
render_class.cached_function.depend_on_row('program.StudentRegistration', lambda reg: {'user': reg.user})
render_class.cached_function.get_or_create_token(('user',))

@cache_inclusion_tag(register, 'inclusion/program/class_catalog_webapp.html')
def render_class_webapp(cls, prog, user=None, filter=False, timeslot=None, checked_in=False):
    """Render the entire class for the webapp, including user-specific parts.

    Calls render_class_core for non-user-specific parts.
    """
    context = _render_class_helper(cls,  user, filter, timeslot, webapp = True, prereg_suffix = 'onsiteaddclass')
    context['checked_in'] = checked_in
    return context
render_class_webapp.cached_function.depend_on_cache(render_class_core.cached_function, lambda cls=wildcard, **kwargs: {'cls': cls})
render_class_webapp.cached_function.get_or_create_token(('cls',))
# We need to depend on not only the user's StudentRegistrations for this
# section, but in fact on their StudentRegistrations for all sections, because
# of things like lunch constraints -- a change made in another block could
# affect whether you can add a class in this one.  So we depend on all SRs for
# this user.  This only applies to tags that can depend on a user.
render_class_webapp.cached_function.depend_on_row('program.StudentRegistration', lambda reg: {'user': reg.user})
render_class_webapp.cached_function.get_or_create_token(('user',))
render_class_webapp.cached_function.depend_on_row('users.Record', lambda record: {'prog': record.program}, lambda record: record.event == 'attended')

@cache_function
def render_class_direct(cls):
    """Like render_class, but as a function instead of an inclusion tag.

    Used in the main catalog.
    """
    return render_to_string('inclusion/program/class_catalog.html', _render_class_helper(cls))
render_class_direct.depend_on_cache(render_class_core.cached_function, lambda cls=wildcard, **kwargs: {'cls': cls})


def _render_class_helper(cls, user=None, filter=False, timeslot=None, webapp = False, prereg_suffix = 'addclass'):
    """Computes the context for render_class and render_class_direct."""
    scrmi = cls.parent_program.studentclassregmoduleinfo
    crmi = cls.parent_program.classregmoduleinfo

    if timeslot:
        section = cls.get_section(timeslot=timeslot)
    else:
        section = None

    if (crmi.open_class_registration and
            cls.category == cls.parent_program.open_class_category):
        prereg_url = None
    else:
        prereg_url = cls.parent_program.get_learn_url() + prereg_suffix

    if user and prereg_url and timeslot:
        errormsg = cls.cannotAdd(user, which_section=section, webapp = webapp)
    else:
        errormsg = None

    show_class = (not filter) or (not errormsg)

    # Allow tag configuration of whether class descriptions get collapsed
    # when the class is full (default: yes)
    collapse_full = Tag.getBooleanTag('collapse_full_classes', cls.parent_program)

    return {'class':      cls,
            'collapse_full': collapse_full,
            'section':    section,
            'user':       user,
            'prereg_url': prereg_url,
            'errormsg':   errormsg,
            'temp_full_message': scrmi.temporarily_full_text,
            'show_class': show_class}


# The following two need to be inclusion tags rather than template includes
# because we want to cache them.
@cache_inclusion_tag(register, 'inclusion/program/class_catalog_preview.html')
def render_class_preview(cls):
    """Render a class for the teacherreg class preview."""
    return {'class': cls}
render_class_preview.cached_function.depend_on_row(ClassSubject, lambda cls: {'cls': cls})
render_class_preview.cached_function.depend_on_m2m(ClassSubject, 'teachers', lambda cls, user: {'cls': cls})


@cache_inclusion_tag(register, 'inclusion/program/class_catalog_row.html')
def render_class_row(cls):
    """Render a class for the onsite class list."""
    return {'class': cls}
render_class_row.cached_function.depend_on_row(ClassSubject, lambda cls: {'cls': cls})
render_class_row.cached_function.depend_on_row(ClassSection, lambda sec: {'cls': sec.parent_class})
render_class_row.cached_function.depend_on_cache(ClassSection.num_students, lambda self=wildcard, **kwargs: {'cls': self.parent_class})
render_class_row.cached_function.depend_on_m2m(ClassSubject, 'teachers', lambda cls, user: {'cls': cls})
render_class_row.cached_function.depend_on_m2m(ClassSection, 'meeting_times', lambda sec, ts: {'cls': sec.parent_class})
render_class_row.cached_function.depend_on_model('modules.StudentClassRegModuleInfo')
render_class_row.cached_function.depend_on_row('resources.ResourceAssignment', lambda ra: {'cls': ra.target.parent_class})
