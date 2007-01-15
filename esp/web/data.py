from esp.users.models import ESPUser
import django.shortcuts
from esp.web.navBar import makeNavBar
from esp.program.models import Program

def render_to_response(template, requestOrContext, prog = None, context = None):
    # if there are only two arguments
    if context is None and prog is None:
        return django.shortcuts.render_to_response(template, requestOrContext)
    
    if context is not None:
        request = requestOrContext
        if type(prog) == Program and not context.has_key('program'):
            context['program'] = prog
        # create nav bar list
        if not context.has_key('navbar_list'):
            if prog is None:
                context['navbar_list'] = navbar_data
            elif type(prog) == Program:
                context['navbar_list'] = makeNavBar(request.user, prog.anchor)
            else:
                context['navbar_list'] = makeNavBar(request.user, prog)
                
        # get the preload_images list
        if not context.has_key('preload_images'):
                context['preload_images'] = preload_images
        # set the value of logged_in
        if not context.has_key('logged_in'):
            context['logged_in'] = request.user.is_authenticated()
        # upgrade user
        request.user = ESPUser(request.user)
        context['request'] = request
        return django.shortcuts.render_to_response(template, context)
        
    assert False, 'render_to_response expects 2 or 4 arguments.'


navbar_data = [
	{ 'link': '/teach/what-to-teach.html',
	  'text': 'What You Can Teach',
	'indent': False },
	{ 'link': '/teach/prev-classes.html',
	  'text': 'Previous Classes',
	  'indent': False },
	{ 'link': '/teach/teaching-time.html',
	  'text': 'Time Commitments',
	  'indent': False },
	{ 'link': '/teach/training.html',
	  'text': 'Teacher Training',
	  'indent': False },
	{ 'link': '/teach/ta.html',
	  'text': 'Become a TA',
	  'indent': False },
	{ 'link': '/teach/coteach.html',
	  'text': 'Co-Teach',
	  'indent': False },
	{ 'link': '/teach/reimburse.html',
	  'text': 'Reimbursements',
	  'indent': False },
	{ 'link': '/programs/hssp/teach.html',
	  'text': 'HSSP',
	  'indent': False },
	{ 'link': '/programs/hssp/classreg.html',
	  'text': 'Class Registration',
	  'indent': True },
	{ 'link': '/teach/teacherinformation.html',
	  'text': 'Teacher Information',
	  'indent': True },
	{ 'link': '/programs/hssp/summerhssp.html',
	  'text': 'Summer HSSP',
	  'indent': False },
	{ 'link': '/programs/hssp/classreg.html',
	  'text': 'Class Registration',
	  'indent': True },
	{ 'link': '/programs/firehose/teach.html',
	  'text': 'Firehose',
	  'indent': False },
	{ 'link': '/programs/junction/teach.html',
	  'text': 'JUNCTION',
	  'indent': False },
	{ 'link': '/programs/junction/classreg.html',
	  'text': 'Class Registration',
	  'indent': True },
	{ 'link': '/programs/delve/teach.html',
	  'text': 'DELVE (AP Program)',
	  'indent': False }
]

preload_images = [
	'/media/images/level3/nav/home_ro.gif',
	'/media/images/level3/nav/discoveresp_ro.gif',
	'/media/images/level3/nav/takeaclass_ro.gif',
	'/media/images/level3/nav/volunteertoteach_ro.gif',
	'/media/images/level3/nav/getinvolved_ro.gif',
	'/media/images/level3/nav/archivesresources_ro.gif',
	'/media/images/level3/nav/myesp_ro.gif',
	'/media/images/level3/nav/contactinfo_ro.gif'
]
