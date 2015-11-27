from django.conf import settings
from django import template
from django.core.cache import cache
from esp.users.models import ESPUser, AnonymousUser
from urllib import quote as urlencode
from esp.utils.cache_inclusion_tag import cache_inclusion_tag
register = template.Library()

@cache_inclusion_tag(register,'inclusion/web/navbar.html', takes_context = True)
def get_primary_nav(context):
    try:
        user = context['user']
    except KeyError:
        user = AnonymousUser()

    try:
        request = context['request']
    except KeyError:
        return {}

    path = request.path

    path_list = path.strip('/').split('/')

    if path_list[0] not in known_navlinks:
        return {}

    page_setup = {}
    curuser = user

    is_admin = curuser.isAdmin()

    is_onsite = curuser.isOnsite()

    if is_onsite and is_admin:
        cache_key = 'NAVBAR__%s' % urlencode(path)
    else:
        cache_key = None

    try:
        retVal = cache.get(cache_key)
    except:
        retVal = None

    if retVal and cache_key:
        return {'page_setup': retVal,
                'user':       curuser}


    # if we are at a level 2 site, like /myesp/home/
    if len(path_list) == 2 and path.lower() in [ x[2] for x in sections.values() ]:
        page_setup['navlinks'] = []
        page_setup['buttonlocation'] = 'lev2'
        page_setup['stylesheet']     = [ x for x in basic_navlinks if sections[x][0] == path_list[0]][0]+'2'
        for section in basic_navlinks:
            page_setup['navlinks'].append({'id'       : section,
                                           'alt'      : sections[section][1],
                                           'highlight': path.lower() == sections[section][2],
                                           'href'     : sections[section][2]})
            if path.lower() == sections[section][2]:
                page_setup['section'] = {'id': section+'/lev2', 'alt': sections[section][1]}
                context['page_section'] = page_setup['section']
        if is_admin:
            section = 'admin'
            page_setup['navlinks'].append({'id'       : section,
                                           'alt'      : sections[section][1],
                                           'highlight': path.lower() == sections[section][2],
                                           'href'     : sections[section][2]})
        if is_onsite:
            section = 'onsite'
            page_setup['navlinks'].append({'id'       : section,
                                           'alt'      : sections[section][1],
                                           'highlight': path.lower() == sections[section][2],
                                           'href'     : sections[section][2]})
        if cache_key:
            cache.set(cache_key, page_setup, 99999)

        return {'page_setup': page_setup,
                'user':       curuser}

    # this is now level 3
    elif path_list[0] in [ x[0] for x in sections.values() ]:
        page_setup['navlinks'] = []
        page_setup['stylesheet'] = [ x for x in basic_navlinks if sections[x][0] == path_list[0]][0]+'3'

        for section in basic_navlinks:
            if path_list[0] == sections[section][0] and sections[section][4]:

                page_setup['section'] = {'id': section+'/lev3',
                                         'alt': sections[section][1],
                                         'cursection': section}
                context['page_section'] = page_setup['section']
                current_section = section

        for section in basic_navlinks:
            if path_list[0] == sections[section][0]:
                curbuttonloc = 'lev3'
            elif section in sections[current_section][3]:
                curbuttonloc = current_section + '/lev3'
            else:
                curbuttonloc = 'lev3'

            page_setup['navlinks'].append({'id'       : section,
                                           'alt'      : sections[section][1],
                                           'highlight': path_list[0] == sections[section][0] and sections[section][4],
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

        if cache_key:
            cache.set(cache_key, page_setup, 99999)

        return {'page_setup': page_setup,
                'user':       curuser}

    return {'user': curuser}

sections = {'discoveresp'      : ('about',      'Discover ESP',        '/about/index.html',      [], True),
            'takeaclass'       : ('learn',      'Take a Class!',       '/learn/index.html',      ['getinvolved','volunteertoteach'], True),
            'volunteertoteach' : ('teach',      'Volunteer to Teach!', '/teach/index.html',      ['getinvolved'], True),
            'getinvolved'      : ('getinvolved','Get Involved',        '/getinvolved/index.html',['volunteertoteach'], True),
            'archivesresources': ('archives',   'ESP Archives',        '/archives/index.html',   ['takeaclass','getinvolved','volunteertoteach'], True),
            'myesp'            : ('myesp',      'myESP',               '/myesp/home/',           ['takeaclass','getinvolved','volunteertoteach'], True),
            'contactinfo'      : ('about',      'Contact Us!',         '/about/contact.html',    [], False),
            'admin'            : ('admin',      'Admin Section',       '/manage/programs/',          [], False),
            'onsite'           : ('onsite',     'Onsite Registration', '/myesp/onsite/',         [], False)}


known_navlinks = ['about','learn','teach','getinvolved','archives','myesp','contactinfo']
basic_navlinks = ['discoveresp','takeaclass','volunteertoteach','getinvolved','archivesresources','myesp','contactinfo']



