from django import template
from esp.web.util.template import cache_inclusion_tag
from esp.users.models import ESPUser
from esp.program.models import ClassSubject, ClassSection
from esp.cache.key_set import wildcard
    
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

    prog = cls.parent_program

    #   Show e-mail codes?  We need to look in the settings.
    scrmi = cls.parent_program.getModuleExtension('StudentClassRegModuleInfo')

    # Okay, chose a program? Good. Now fetch the color from its hiding place and format it...
    colorstring = prog.getColor()
    if colorstring is not None:
        colorstring = ' background-color:#' + colorstring + ';'
    
    # HACK for Harvard HSSP -- show application counts with enrollment
    if cls.studentappquestion_set.count():
        cls._sections = list(cls.get_sections())
        for sec in cls._sections:
            sec.num_apps = sec.num_students(verbs=['Applied'])

    return {'class': cls,
            'colorstring': colorstring,
            'show_enrollment': scrmi.visible_enrollments,
            'show_emailcodes': scrmi.show_emailcodes,
            'show_meeting_times': scrmi.visible_meeting_times}           
render_class_core.cached_function.depend_on_row(ClassSubject, lambda cls: {'cls': cls})
render_class_core.cached_function.depend_on_row(ClassSection, lambda sec: {'cls': sec.parent_class})
render_class_core.cached_function.depend_on_cache(ClassSubject.title, lambda self=wildcard, **kwargs: {'cls': self})
render_class_core.cached_function.depend_on_cache(ClassSection.num_students, lambda self=wildcard, **kwargs: {'cls': self.parent_class})
render_class_core.cached_function.depend_on_m2m(ClassSection, 'meeting_times', lambda sec, ts: {'cls': sec.parent_class})

@cache_inclusion_tag(register, 'inclusion/program/class_catalog.html')
def render_class(cls, user=None, prereg_url=None, filter=False, timeslot=None):
    errormsg = None
    
    if timeslot:
        section = cls.get_section(timeslot=timeslot)
    else:
        section = None

    #   Add ajax_addclass to prereg_url if registering from catalog is allowed
    ajax_prereg_url = None
    scrmi = cls.parent_program.getModuleExtension('StudentClassRegModuleInfo')

    #   Ensure cached catalog shows buttons and fillslots don't
    if scrmi.register_from_catalog and not timeslot:
        ajax_prereg_url = cls.parent_program.get_learn_url() + 'ajax_addclass'

    prereg_url = cls.parent_program.get_learn_url() + 'addclass'

    if user and prereg_url and timeslot:
        error1 = cls.cannotAdd(user)
        # If we can't add the class at all, then we take that error message
        if error1:
            errormsg = error1
        else:  # there's some section for which we can add this class; does that hold for this one?
            if section:
                errormsg = section.cannotAdd(user)
        
    show_class =  (not filter) or (not errormsg)
    
    return {'class':      cls,
            'section':    section,
            'user':       user,
            'prereg_url': prereg_url,
            'ajax_prereg_url': ajax_prereg_url,
            'errormsg':   errormsg,
            'temp_full_message': scrmi.temporarily_full_text,
            'show_class': show_class}
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
           
