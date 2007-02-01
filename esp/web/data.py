from esp.users.models import ESPUser
from esp.web.navBar import makeNavBar
import django.shortcuts
from esp.web.navBar import makeNavBar
from esp.program.models import Program
from esp.qsd.models import ESPQuotations

def render_to_response(template, requestOrContext, prog = None, context = None):
    # if there are only two arguments
    if context is None and prog is None:
        return django.shortcuts.render_to_response(template, requestOrContext)
    
    if context is not None:
        request = requestOrContext

        context['page_setup'] = get_page_setup(request)
        
        section = ''


        if type(prog) == tuple:
            section = prog[1]
            prog = prog[0]

        if not context.has_key('program'):  

            if type(prog) == Program:
                context['program'] = prog
            # create nav bar list
        if not context.has_key('navbar_list'):
            if prog is None:
                context['navbar_list'] = navbar_data
            elif type(prog) == Program:
                context['navbar_list'] = makeNavBar(request.user, prog.anchor, section)
            else:
                context['navbar_list'] = makeNavBar(request.user, prog, section)
        context['randquote'] = ESPQuotations.getQuotation()   
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


def get_page_setup(request):
    path = request.path.strip('/').split('/')
    if path[0] not in known_navlinks:
        return False

    page_setup = {}

    is_admin = ESPUser(request.user).isAdmin()
    
    
    if len(path) == 2 and request.path.lower() in [ x[2] for x in section_convert.values() ]:
        page_setup['navlinks'] = []
        page_setup['buttonlocation'] = 'lev2'
        page_setup['stylesheet']     = [ x for x in basic_navlinks if section_convert[x][0] == path[0]][0]+'2'
        for section in basic_navlinks:
            page_setup['navlinks'].append({'id'       : section,
                                           'alt'      : section_convert[section][1],
                                           'highlight': request.path.lower() == section_convert[section][2],
                                           'href'     : section_convert[section][2]})
            if request.path.lower() == section_convert[section][2]:
                page_setup['section'] = {'id': section+'/lev2', 'alt': section_convert[section][1]}
        if is_admin:
            section = 'admin'
            page_setup['navlinks'].append({'id'       : section,
                                           'alt'      : section_convert[section][1],
                                           'highlight': request.path.lower() == section_convert[section][2],
                                           'href'     : section_convert[section][2]})
        return page_setup
    
    elif path[0] in known_navlinks:
        page_setup['navlinks'] = []
        page_setup['buttonlocation'] = 'lev3'
        page_setup['stylesheet'] = [ x for x in basic_navlinks if section_convert[x][0] == path[0]][0]+'3'
        for section in basic_navlinks:
            if path[0] == section_convert[section][0]:
                page_setup['section'] = {'id': section+'/lev3',
                                         'alt': section_convert[section][1],
                                         'cursection': section}
                page_setup['buttonlocation'] = section+'/lev3'
                
        for section in basic_navlinks:
            page_setup['navlinks'].append({'id'       : section,
                                           'alt'      : section_convert[section][1],
                                           'highlight': path[0] == section_convert[section][0],
                                           'href'     : section_convert[section][2]})


        if is_admin:
            section = 'admin'
            page_setup['navlinks'].append({'id'       : section,
                                           'alt'      : section_convert[section][1],
                                           'highlight': path[0] == section_convert[section][0],
                                           'href'     : section_convert[section][2]})
        return page_setup

    return False

known_navlinks = ['about','learn','teach','getinvolved','archives','myesp','contactinfo']
basic_navlinks = ['discoveresp','takeaclass','volunteertoteach','getinvolved','archivesresources','myesp','contactinfo']

section_convert = {'volunteertoteach' : ('teach', 'Volunteer to Teach!', '/teach/index.html'),
                   'takeaclass'       : ('learn', 'Take a Class!', '/learn/index.html'),
                   'discoveresp'      : ('about', 'Discover ESP', '/about/index.html'),
                   'myesp'            : ('myesp', 'myESP', '/myesp/home/'),
                   'getinvolved'      : ('getinvolved', 'Get Involved!','/getinvolved/index.html'),
                   'archivesresources': ('archives', 'ESP Archives','/archives/index.html'),
                   'contactinfo'      : ('about', 'Contact Us','/about/contact.html'),
                   'admin'            : ('admin', 'Admin Section', '/myesp/admin/')}


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
