from django import template
from django.template.loader import render_to_string
from esp.web.util.template import cache_inclusion_tag
from esp.cache import cache_function
from esp.qsdmedia.models import Media as QSDMedia
from esp.program.models import ClassSubject, ClassSection, StudentAppQuestion, StudentRegistration
from esp.program.modules.module_ext import StudentClassRegModuleInfo, ClassRegModuleInfo
from esp.cache.key_set import wildcard
from esp.tagdict.models import Tag
    
register = template.Library()

def get_smallest_section(cls, timeslot=None):
    if timeslot:
        sections = cls.sections.filter(meeting_times=timeslot)
    else:
        sections = cls.sections.all()

    if sections.count() > 0:
        min_count = 9999
        min_index = -1
        for i in range(0, sections.count()):
            q = sections[i].num_students()
            if q < min_count:
                min_index = i
                min_count = q
        section = sections[min_index]
    else:
        section = None

    return section

@cache_inclusion_tag(register, 'inclusion/program/class_catalog_core.html')
def render_class_core(cls):
    return render_class_core_helper(cls)
render_class_core.cached_function.depend_on_row(ClassSubject, lambda cls: {'cls': cls})
render_class_core.cached_function.depend_on_row(ClassSection, lambda sec: {'cls': sec.parent_class})
render_class_core.cached_function.depend_on_cache(ClassSection.num_students, lambda self=wildcard, **kwargs: {'cls': self.parent_class})
render_class_core.cached_function.depend_on_m2m(ClassSection, 'meeting_times', lambda sec, ts: {'cls': sec.parent_class})
render_class_core.cached_function.depend_on_row(StudentAppQuestion, lambda ques: {'cls': ques.subject})
render_class_core.cached_function.depend_on_row(QSDMedia, lambda media: {'cls': media.owner}, lambda media: isinstance(media.owner, ClassSubject))
render_class_core.cached_function.depend_on_model('modules.StudentClassRegModuleInfo')
render_class_core.cached_function.depend_on_model('modules.ClassRegModuleInfo')
render_class_core.cached_function.depend_on_model('tagdict.Tag')

def render_class_core_helper(cls, prog=None, scrmi=None, colorstring=None, collapse_full_classes=None):
    if not prog:
        prog = cls.parent_program

    #   Show e-mail codes?  We need to look in the settings.
    if not scrmi:
        scrmi = cls.parent_program.getModuleExtension('StudentClassRegModuleInfo')

    # Okay, chose a program? Good. Now fetch the color from its hiding place and format it...
    if not colorstring:
        colorstring = prog.getColor()
        if colorstring is not None:
            colorstring = ' background-color:#' + colorstring + ';'
    
    # HACK for Harvard HSSP -- show application counts with enrollment
    #if cls.studentappquestion_set.count():
    #    cls._sections = list(cls.get_sections())
    #    for sec in cls._sections:
    #        sec.num_apps = sec.num_students(verbs=['Applied'])

    # Allow tag configuration of whether class descriptions get collapsed
    # when the class is full (default: yes)
    if collapse_full_classes is None:
        collapse_full_classes = ('false' not in Tag.getProgramTag('collapse_full_classes', prog, 'True').lower())

    return {'class': cls,
            'collapse_full': collapse_full_classes,
            'colorstring': colorstring,
            'show_enrollment': scrmi.visible_enrollments,
            'show_emailcodes': scrmi.show_emailcodes,
            'show_meeting_times': scrmi.visible_meeting_times}           

@cache_inclusion_tag(register, 'inclusion/program/class_catalog.html', disable=True)
def render_class(cls, user=None, prereg_url=None, filter=False, timeslot=None):
    return render_class_helper(cls, user, prereg_url, filter, timeslot)
render_class.cached_function.depend_on_cache(render_class_core.cached_function, lambda cls=wildcard, **kwargs: {'cls': cls})
render_class.cached_function.get_or_create_token(('cls',))
# We need to depend on not only the user's StudentRegistrations for this
# section, but in fact on their StudentRegistrations for all sections, because
# of things like lunch constraints -- a change made in another block could
# affect whether you can add a class in this one.  So we depend on all SRs for
# this user.
render_class.cached_function.depend_on_row('program.StudentRegistration', lambda reg: {'user': reg.user})
render_class.cached_function.get_or_create_token(('user',))

@cache_function
def render_class_direct(cls, user=None, prereg_url=None, filter=False, timeslot=None):
    return render_to_string('inclusion/program/class_catalog.html', render_class_helper(cls))
render_class_direct.get_or_create_token(('cls',))
render_class_direct.depend_on_cache(render_class_core.cached_function, lambda cls=wildcard, **kwargs: {'cls': cls})

def render_class_helper(cls, user=None, prereg_url=None, filter=False, timeslot=None):
    errormsg = None
    
    if timeslot:
        section = cls.get_section(timeslot=timeslot)
    else:
        section = None

    scrmi = cls.parent_program.getModuleExtension('StudentClassRegModuleInfo')
    crmi = cls.parent_program.getModuleExtension('ClassRegModuleInfo')

    #   Ensure cached catalog shows buttons and fillslots don't

    prereg_url = None
    if not (crmi.open_class_registration and cls.category == cls.parent_program.open_class_category):
        prereg_url = cls.parent_program.get_learn_url() + 'addclass'

    if user and prereg_url and timeslot:
        errormsg = cls.cannotAdd(user, which_section=section)
        
    show_class =  (not filter) or (not errormsg)
    
    return {'class':      cls,
            'section':    section,
            'user':       user,
            'prereg_url': prereg_url,
            'errormsg':   errormsg,
            'temp_full_message': scrmi.temporarily_full_text,
            'show_class': show_class,
            'hide_full': Tag.getBooleanTag('hide_full_classes', cls.parent_program, False)}
render_class.cached_function.depend_on_cache(render_class_core.cached_function, lambda cls=wildcard, **kwargs: {'cls': cls})

@cache_inclusion_tag(register, 'inclusion/program/class_catalog_swap.html')
def render_class_swap(cls, swap_class, user=None, prereg_url=None, filter=False):
    errormsg = None

    if user and prereg_url:
        errormsg = cls.cannotAdd(user, True, request=request)
        if errormsg == 'Conflicts with your schedule!':
            errormsg = None
            for currentclass in user.getEnrolledClasses(cls.parent_program).exclude(id=swap_class.id):
                for time in currentclass.meeting_times.all():
                    if cls.meeting_times.filter(id = time.id).count() > 0:
                        errormsg = 'Conflicts with your schedule!'
    
    if cls.id == swap_class.id:
        errormsg = '(You are currently registered for this class.)'
    
    show_class =  (not filter) or (not errormsg)
    
    
    return {'class':      cls,
            'user':       user,
            'prereg_url': prereg_url,
            'errormsg':   errormsg,
            'show_class': show_class}

@cache_inclusion_tag(register, 'inclusion/program/class_catalog_minimal.html')
def render_class_minimal(cls, user=None, prereg_url=None, filter=False):
    errormsg = None

    if user and prereg_url:
        errormsg = cls.cannotAdd(user, True)

    show_class =  (not filter) or (not errormsg)
    
    
    return {'class':      cls,
            'user':       user,
            'prereg_url': prereg_url,
            'errormsg':   errormsg,
            'show_class': show_class}
            
@cache_inclusion_tag(register, 'inclusion/program/class_catalog_current.html')
def render_class_current(cls, user=None, prereg_url=None, filter=False):
    errormsg = None

    if user and prereg_url:
        errormsg = cls.cannotAdd(user, True)

    show_class =  (not filter) or (not errormsg)

    return {'class':      cls,
            'show_class': show_class}
                        
            
@cache_inclusion_tag(register, 'inclusion/program/class_catalog_preview.html')
def render_class_preview(cls, user=None, prereg_url=None, filter=False):
    errormsg = None

    if user and prereg_url:
        errormsg = cls.cannotAdd(user, True)

    show_class =  (not filter) or (not errormsg)
    
    
    return {'class':      cls,
            'user':       user,
            'prereg_url': prereg_url,
            'errormsg':   errormsg,
            'show_class': show_class}

@cache_inclusion_tag(register, 'inclusion/program/class_catalog_row.html')
def render_class_row(cls, user=None, prereg_url=None, filter=False):
    errormsg = None

    if user and prereg_url:
        errormsg = cls.cannotAdd(user, True)

    show_class =  (not filter) or (not errormsg)
    
    
    return {'class':      cls,
            'user':       user,
            'prereg_url': prereg_url,
            'errormsg':   errormsg,
            'show_class': show_class}
           
