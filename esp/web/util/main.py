from esp.users.models import ESPUser
import django.shortcuts
from esp.web.util.navBar import makeNavBar
from esp.program.models import Program
from esp.qsd.models import ESPQuotations
from esp.middleware import ESPError

def get_from_id(id, module, strtype = 'object', error = True):
    """ This function will get an object from its id, and return an appropriate error if need be. """
    from esp.users.models import ESPUser

    try:
        newid    = int(id)
        foundobj = module.objects.get(id = newid)
        if module == ESPUser:
            foundobj = ESPUser(foundobj)
    except:
        if error:
            raise ESPError(False), 'Could not find the %s with id %s.' % (strtype, id)
        return None
    return foundobj
    


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
        if context.has_key('qsd') and context['qsd'] == True:
            context['randquote'] = ESPQuotations.getQuotation()
        else:
            context['randquote'] = False
            
        # get the preload_images list
        if not context.has_key('preload_images'):
                context['preload_images'] = preload_images
        # set the value of logged_in
        if not context.has_key('logged_in'):
            context['logged_in'] = request.user.is_authenticated()
        # upgrade user
        request.user = ESPUser(request.user)
        request.user.updateOnsite(request)
        context['request'] = request
        return django.shortcuts.render_to_response(template, context)
        
    assert False, 'render_to_response expects 2 or 4 arguments.'


def get_page_setup(request):
    path = request.path.strip('/').split('/')
    if path[0] not in known_navlinks:
        return False

    page_setup = {}

    is_admin = ESPUser(request.user).isAdmin()
    curuser = ESPUser(request.user)
    
    is_onsite = ESPUser(request.user).isOnsite()
    
    # if we are at a level 2 site, like /myesp/home/
    if len(path) == 2 and request.path.lower() in [ x[2] for x in sections.values() ]:
        page_setup['navlinks'] = []
        page_setup['buttonlocation'] = 'lev2'
        page_setup['stylesheet']     = [ x for x in basic_navlinks if sections[x][0] == path[0]][0]+'2'
        for section in basic_navlinks:
            page_setup['navlinks'].append({'id'       : section,
                                           'alt'      : sections[section][1],
                                           'highlight': request.path.lower() == sections[section][2],
                                           'href'     : sections[section][2]})
            if request.path.lower() == sections[section][2]:
                page_setup['section'] = {'id': section+'/lev2', 'alt': sections[section][1]}
        if is_admin:
            section = 'admin'
            page_setup['navlinks'].append({'id'       : section,
                                           'alt'      : sections[section][1],
                                           'highlight': request.path.lower() == sections[section][2],
                                           'href'     : sections[section][2]})
        if is_onsite:
            section = 'onsite'
            page_setup['navlinks'].append({'id'       : section,
                                           'alt'      : sections[section][1],
                                           'highlight': request.path.lower() == sections[section][2],
                                           'href'     : sections[section][2]})
        return page_setup
    
    # this is now level 3
    elif path[0] in [ x[0] for x in sections.values() ]:
        page_setup['navlinks'] = []
        page_setup['stylesheet'] = [ x for x in basic_navlinks if sections[x][0] == path[0]][0]+'3'

        for section in basic_navlinks:
            if path[0] == sections[section][0] and sections[section][4]:
                page_setup['section'] = {'id': section+'/lev3',
                                         'alt': sections[section][1],
                                         'cursection': section}
                current_section = section
                
        for section in basic_navlinks:
            if path[0] == sections[section][0]:
                curbuttonloc = 'lev3'
            elif section in sections[current_section][3]:
                curbuttonloc = current_section + '/lev3'
            else:
                curbuttonloc = 'lev3'
                
            page_setup['navlinks'].append({'id'       : section,
                                           'alt'      : sections[section][1],
                                           'highlight': path[0] == sections[section][0] and sections[section][4],
                                           'href'     : sections[section][2],
                                           'buttonloc': curbuttonloc})
            

        if is_admin:
            section = 'admin'
            page_setup['navlinks'].append({'id'       : section,
                                           'alt'      : sections[section][1],
                                           'highlight': False,
                                           'href'     : sections[section][2],
                                           'buttonloc': 'lev2'})
        if is_onsite:
            section = 'onsite'
            page_setup['navlinks'].append({'id'       : section,
                                           'alt'      : sections[section][1],
                                           'highlight': False,
                                           'href'     : sections[section][2],
                                           'buttonloc': 'lev2'})
            
        return page_setup

    return False

sections = {'discoveresp'      : ('about',      'Discover ESP',        '/about/index.html',      [], True),
            'takeaclass'       : ('learn',      'Take a Class!',       '/learn/index.html',      ['getinvolved','volunteertoteach'], True),
            'volunteertoteach' : ('teach',      'Volunteer to Teach!', '/teach/index.html',      ['getinvolved'], True),
            'getinvolved'      : ('getinvolved','Get Involved',        '/getinvolved/index.html',['volunteertoteach'], True),
            'archivesresources': ('archives',   'ESP Archives',        '/archives/index.html',   ['takeaclass','getinvolved','volunteertoteach'], True),
            'myesp'            : ('myesp',      'myESP',               '/myesp/home/',           ['takeaclass','getinvolved','volunteertoteach'], True),
            'contactinfo'      : ('about',      'Contact Us!',         '/about/contact.html',    [], False),
            'admin'            : ('admin',      'Admin Section',       '/myesp/admin/',          [], False),
            'onsite'           : ('onsite',     'Onsite Registration', '/myesp/onsite/',         [], False)}


known_navlinks = ['about','learn','teach','getinvolved','archives','myesp','contactinfo']
basic_navlinks = ['discoveresp','takeaclass','volunteertoteach','getinvolved','archivesresources','myesp','contactinfo']



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
