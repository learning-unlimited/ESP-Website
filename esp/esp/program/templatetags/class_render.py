from django import template
from esp.web.util.template import cache_inclusion_tag
    
register = template.Library()

def cache_key_func(cls, user=None, prereg_url=None, filter=False):
    if not user:
        return 'CLASS_DISPLAY__%s' % cls.id

    return None

@cache_inclusion_tag(register, 'inclusion/program/class_catalog.html', cache_key_func=cache_key_func)
def render_class(cls, user=None, prereg_url=None, filter=False):
    errormsg = None

    if user and prereg_url:
        errormsg = cls.cannotAdd(user)

    show_class =  (not filter) or (not errormsg)
    
    
    return {'class':      cls,
            'user':       user,
            'prereg_url': prereg_url,
            'errormsg':   errormsg,
            'show_class': show_class}
           
