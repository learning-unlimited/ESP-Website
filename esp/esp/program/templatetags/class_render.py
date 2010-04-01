from django import template
from esp.web.util.template import cache_inclusion_tag
from esp.users.models import ESPUser
    
register = template.Library()

def cache_key_func(cls, user=None, prereg_url=None, filter=False, timeslot=None, request=None):
    # Try more caching, our code screens the classes anyway.
    if timeslot:
        if user:
            return 'CLASS_DISPLAY__%s_%s_%s' % (cls.id, timeslot.id, user.id)
        else:
            return 'CLASS_DISPLAY__%s_%s' % (cls.id, timeslot.id)
    else:
        if user:
            return 'CLASS_DISPLAY__%s_%s' % (cls.id, user.id)
        else:
            return 'CLASS_DISPLAY__%s' % (cls.id)

def core_cache_key_func(cls):
    return 'CLASS_CORE_DISPLAY__%s' % cls.id

def minimal_cache_key_func(cls, user=None, prereg_url=None, filter=False, request=None):
    if not user or not prereg_url:
        return 'CLASS_MINDISPLAY__%s' % cls.id
    return None

def current_cache_key_func(cls, user=None, prereg_url=None, filter=False, request=None):
    if not user or not prereg_url:
        return 'CLASS_CURRENT__%s' % cls.id
    return None

def preview_cache_key_func(cls, user=None, prereg_url=None, filter=False, request=None):
    if not user or not prereg_url:
        return 'CLASS_PREVIEW__%s' % cls.id
    return None

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

@cache_inclusion_tag(register, 'inclusion/program/class_catalog_core.html', cache_key_func=core_cache_key_func)
def render_class_core(cls):

    prog = cls.parent_program

    #   Show e-mail codes?  We need to look in the settings.
    scrmi = cls.parent_program.getModuleExtension('StudentClassRegModuleInfo')

    # Okay, chose a program? Good. Now fetch the color from its hiding place and format it...
    colorstring = prog.getColor()
    if colorstring is not None:
        colorstring = ' background-color:#' + colorstring + ';'

    return {'class': cls,
            'isfull': (cls.isFull()),
            'colorstring': colorstring,
            'show_enrollment': scrmi.visible_enrollments,
            'show_emailcodes': scrmi.show_emailcodes,
            'show_meeting_times': scrmi.visible_meeting_times}
            
@cache_inclusion_tag(register, 'inclusion/program/class_catalog.html', cache_key_func=cache_key_func, cache_time=60)
def render_class(cls, user=None, prereg_url=None, filter=False, timeslot=None, request=None):
    errormsg = None

    section = cls.get_section(timeslot=timeslot)
        
    #   Add ajax_addclass to prereg_url if registering from catalog is allowed
    scrmi = cls.parent_program.getModuleExtension('StudentClassRegModuleInfo')
    if prereg_url is None and scrmi.register_from_catalog:
        if user is not None and ESPUser(user).is_authenticated():
            prereg_url = cls.parent_program.get_learn_url() + 'ajax_addclass'

    if user and prereg_url:
        error1 = cls.cannotAdd(user, True, request=request)
        # If we can't add the class at all, then we take that error message
        if error1:
            errormsg = error1
        else:  # there's some section for which we can add this class; does that hold for this one?
            errormsg = section.cannotAdd(user, True, request=request)
        
    show_class =  (not filter) or (not errormsg)
    
    return {'class':      cls,
            'section':    section,
            'user':       user,
            'prereg_url': prereg_url,
            'errormsg':   errormsg,
            'temp_full_message': scrmi.temporarily_full_text,
            'show_class': show_class}

# We're not caching this yet because I doubt people will hit this function the same way repeatedly--same user and all.
# The lambda is there because cache_inclusion_tag doesn't like receiving cache_key_func=None. -ageng 2008-02-18
@cache_inclusion_tag(register, 'inclusion/program/class_catalog_swap.html', cache_key_func=lambda a, b, c, d, e, f: None)
def render_class_swap(cls, swap_class, user=None, prereg_url=None, filter=False, request=None):
    errormsg = None

    if user and prereg_url:
        errormsg = cls.cannotAdd(user, True, request=request)
        if errormsg == 'Conflicts with your schedule!':
            errormsg = None
            for currentclass in user.getEnrolledClasses(cls.parent_program, request).exclude(id=swap_class.id):
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

@cache_inclusion_tag(register, 'inclusion/program/class_catalog_minimal.html', cache_key_func=minimal_cache_key_func)
def render_class_minimal(cls, user=None, prereg_url=None, filter=False, request=None):
    errormsg = None

    if user and prereg_url:
        errormsg = cls.cannotAdd(user, True, request=request)

    show_class =  (not filter) or (not errormsg)
    
    
    return {'class':      cls,
            'user':       user,
            'prereg_url': prereg_url,
            'errormsg':   errormsg,
            'show_class': show_class}
            
@cache_inclusion_tag(register, 'inclusion/program/class_catalog_current.html', cache_key_func=current_cache_key_func)
def render_class_current(cls, user=None, prereg_url=None, filter=False, request=None):
    errormsg = None

    if user and prereg_url:
        errormsg = cls.cannotAdd(user, True, request=request)

    show_class =  (not filter) or (not errormsg)

    return {'class':      cls,
            'show_class': show_class}
                        
            
@cache_inclusion_tag(register, 'inclusion/program/class_catalog_preview.html', cache_key_func=preview_cache_key_func)
def render_class_preview(cls, user=None, prereg_url=None, filter=False, request=None):
    errormsg = None

    if user and prereg_url:
        errormsg = cls.cannotAdd(user, True, request=request)

    show_class =  (not filter) or (not errormsg)
    
    
    return {'class':      cls,
            'user':       user,
            'prereg_url': prereg_url,
            'errormsg':   errormsg,
            'show_class': show_class}

@cache_inclusion_tag(register, 'inclusion/program/class_catalog_row.html', cache_key_func=minimal_cache_key_func)
def render_class_row(cls, user=None, prereg_url=None, filter=False, request=None):
    errormsg = None

    if user and prereg_url:
        errormsg = cls.cannotAdd(user, True, request=request)

    show_class =  (not filter) or (not errormsg)
    
    
    return {'class':      cls,
            'user':       user,
            'prereg_url': prereg_url,
            'errormsg':   errormsg,
            'show_class': show_class}
           
