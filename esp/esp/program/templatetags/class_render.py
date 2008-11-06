from django import template
from esp.web.util.template import cache_inclusion_tag
    
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


@cache_inclusion_tag(register, 'inclusion/program/class_catalog_core.html', cache_key_func=core_cache_key_func)
def render_class_core(cls):

    prog = cls.parent_program
    
    # Show enrollment?
    show_enrollment = prog.visibleEnrollments()
    
    # Check to see if this is an implied class; if so, grab the parent program and use its colors instead
    if prog.getParentProgram() is not None:
        if cls.id in prog.getParentProgram().class_ids_implied():
            prog = prog.getParentProgram()
    
    # Okay, chose a program? Good. Now fetch the color from its hiding place and format it...
    colorstring = prog.getColor()
    if colorstring is not None:
        colorstring = ' background-color:#' + colorstring + ';'
    
    return {'class': cls,
            'isfull': (cls.isFull()),
            'colorstring': colorstring,
            'show_enrollment': show_enrollment }
            
@cache_inclusion_tag(register, 'inclusion/program/class_catalog.html', cache_key_func=cache_key_func)
def render_class(cls, user=None, prereg_url=None, filter=False, timeslot=None, request=None):
    errormsg = None

    if user and prereg_url:
        errormsg = cls.cannotAdd(user, True, request=request)
    
    show_class =  (not filter) or (not errormsg)
    
    section = cls.get_section(timeslot=timeslot)
    
    return {'class':      cls,
            'section':    section,
            'user':       user,
            'prereg_url': prereg_url,
            'errormsg':   errormsg,
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
           
