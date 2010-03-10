
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""
from esp.qsd.models import QuasiStaticData
from django.contrib.auth.models import User
from esp.users.models import ContactInfo, UserBit, GetNodeOrNoBits
from esp.datatree.models import *
from esp.web.views.navBar import makeNavBar
from esp.web.models import NavBarEntry, NavBarCategory
from esp.web.util.main import render_to_response
from django.http import HttpResponse, Http404, HttpResponseNotAllowed
from esp.qsdmedia.models import Media
from esp.lib.markdownaddons import ESPMarkdown
from esp.settings import MEDIA_ROOT, MEDIA_URL
from os.path import basename, dirname
from datetime import datetime
from django.core.cache import cache
from django.template.defaultfilters import urlencode
from esp.datatree.decorators import branch_find
from esp.middleware import ESPError, Http403
from django.utils.cache import add_never_cache_headers, patch_cache_control, patch_vary_headers
from django.views.decorators.vary import vary_on_cookie
from django.views.decorators.cache import cache_control

# default edit permission
EDIT_PERM = 'V/Administer/Edit'

# spacing between separate nav bar entries
DEFAULT_SPACING = 5

def handle_ajax_mover(method):
    """
    Takes a view and wraps it in such a way that a user can
    submit AJAX requests for changing the order of navbar entries.
    """

    def ajax_mover(request, *args, **kwargs):
        if not request.GET.has_key('ajax_movepage') or \
           not request.GET.has_key('seq'):
            return method(request, *args, **kwargs)

        START = 'nav_entry__'

        entries = request.GET['seq'].strip(',').split(',')
        try:
            entries = [x[len(START):] for x in entries]
        except:
            return method(request, *args, **kwargs)

        # using some good magic we get a list of tree_node common
        # ancestors
        tree_nodes = DataTree.get_only_parents(DataTree.objects.filter(navbar__in = entries))

        edit_verb = GetNode(EDIT_PERM)
        for node in tree_nodes:
            if not UserBit.UserHasPerms(request.user,
                            node,
                            edit_verb):
                return method(request, *args, **kwargs)

        # now we've properly assessed the person knows what
        # they're doing. We actually do the stuff we wanted.
        rank = 0
        for entry in entries:
            try:
                navbar = NavBarEntry.objects.get(pk = entry)
                navbar.sort_rank = rank
                navbar.save()
                rank += DEFAULT_SPACING
            except:
                pass

        return HttpResponse('Success')

    return ajax_mover



@handle_ajax_mover
@branch_find
@cache_control(max_age=180)
def qsd(request, branch, name, section, action):

    READ_VERB = 'V/Flags/Public'
    EDIT_VERB = 'V/Administer/Edit/QSD'

    if action == 'read':
        base_url = request.path[:-5]
    else:
        base_url = request.path[:(-len(action)-6)]

    # Detect edit authorizations
    have_edit = UserBit.UserHasPerms(request.user, branch, EDIT_VERB)

    if have_edit:
        have_read = True
    else:
        have_read = UserBit.UserHasPerms(request.user, branch, READ_VERB)

    if not have_read and action == 'read':
        raise Http403, "You do not have permission to access this page."

    # Fetch the QSD object
    try:
        qsd_rec = QuasiStaticData.objects.get_by_path__name(branch, name)
        if qsd_rec.disabled:
            raise QuasiStaticData.DoesNotExist

    except QuasiStaticData.DoesNotExist:
        if have_edit:
            if action in ('edit','create',):
                qsd_rec = QuasiStaticData()
                qsd_rec.path = branch
                qsd_rec.name = name
                qsd_rec.nav_category = NavBarCategory.default()
                qsd_rec.title = 'New Page'
                qsd_rec.content = 'Please insert your text here'
                qsd_rec.create_date = datetime.now()
                qsd_rec.keywords = ''
                qsd_rec.description = ''
                action = 'edit'

            if (action == 'read'):
                edit_link = base_url+'.edit.html'
                return render_to_response('qsd/nopage_edit.html', request, (branch, section), {'edit_link': edit_link})
        else:
            if action == 'read':
                raise Http404, 'This page does not exist.'
            else:
                raise Http403, 'Sorry, you can not modify <tt>%s</tt>.' % request.path

    if action == 'create':
        action = 'edit'

    # Detect the standard read verb
    if action == 'read':        
        if not have_read:
            raise Http403, 'You do not have permission to read this page.'

        # Render response
        response = render_to_response('qsd/qsd.html', request, (branch, section), {
            'title': qsd_rec.title,
            'nav_category': qsd_rec.nav_category, 
            'content': qsd_rec.html(),
            'qsdrec': qsd_rec,
            'have_edit': have_edit,
            'edit_url': base_url + ".edit.html" })

        patch_vary_headers(response, ['Cookie'])
        if have_edit:
            add_never_cache_headers(response)
            patch_cache_control(response, no_cache=True, no_store=True)
        else:
            patch_cache_control(response, max_age=3600, public=True)

        return response

            
    # Detect POST
    if request.POST.has_key('post_edit'):
        if not have_edit:
            raise Http403, "Sorry, you do not have permission to edit this page."
        
        # Arguably, this should retrieve the DB object, use the .copy()
        # method, and then update it. Doing it this way saves a DB call
        # (and requires me to make fewer changes).
        qsd_rec_new = QuasiStaticData()
        qsd_rec_new.path = branch
        qsd_rec_new.name = name
        qsd_rec_new.author = request.user
        qsd_rec_new.nav_category = NavBarCategory.objects.get(id=request.POST['nav_category'])
        qsd_rec_new.content = request.POST['content']
        qsd_rec_new.title = request.POST['title']
        qsd_rec_new.description = request.POST['description']
        qsd_rec_new.keywords    = request.POST['keywords']
        qsd_rec_new.save()

        qsd_rec = qsd_rec_new

        # If any files were uploaded, save them
        for name, file in request.FILES.iteritems():
            m = Media()

            # Strip "media/" from FILE, and strip the file name; just return the path
            path = dirname(name[9:])
            if path == '':
                m.anchor = qsd_rec.path
            else:
                m.anchor = GetNode('Q/' + dirname(name))
                
            # Do we want a better/manual mechanism for setting friendly_name?
            m.friendly_name = basename(name)
            
            m.format = ''

            local_filename = name
            if name[:9] == 'qsdmedia/':
                local_filename = name[9:]
                    
            m.handle_file(file, local_filename)
            m.save()


    # Detect the edit verb
    if action == 'edit':
        # Enforce authorizations (FIXME: SHOW A REAL ERROR!)
        if not have_edit:
            raise ESPError(False), "You don't have permission to edit this page."

        m = ESPMarkdown(qsd_rec.content, media={})

        m.toString()
#        assert False, m.BrokenLinks()
        
        # Render an edit form
        return render_to_response('qsd/qsd_edit.html', request, (branch, section), {
            'title'        : qsd_rec.title,
            'content'      : qsd_rec.content,
            'keywords'     : qsd_rec.keywords,
            'description'  : qsd_rec.description,
            'nav_category' : qsd_rec.nav_category, 
            'nav_categories': NavBarCategory.objects.all(),
            'qsdrec'       : qsd_rec,
            'qsd'          : True,
            'missing_files': m.BrokenLinks(),
            'target_url'   : base_url.split("/")[-1] + ".edit.html",
            'return_to_view': base_url.split("/")[-1] + ".html" })

    
    # Operation Complete!
    assert False, 'Unexpected QSD operation'

def ajax_qsd(request):
    """ Ajax function for in-line QSD editing.  """
    from django.utils import simplejson
    from esp.lib.templatetags.markdown import markdown
    from esp.web.templatetags.latex import teximages
    from esp.web.templatetags.smartypants import smartypants

    EDIT_VERB = 'V/Administer/Edit/QSD'

    result = {}
    post_dict = request.POST.copy()

    if ( request.user.id is None ):
        return HttpResponse(content='Oops! Your session expired!\nPlease open another window, log in, and try again.\nYour changes will not be lost if you keep this page open.', status=500)
    if post_dict['cmd'] == "update":
        qsdold = QuasiStaticData.objects.get(id=post_dict['id'])
        if not UserBit.UserHasPerms(request.user, qsdold.path, EDIT_VERB):
            return HttpResponse(content='Sorry, you do not have permission to edit this page.', status=500)
        qsd = qsdold.copy()
        qsd.content = post_dict['data']
        qsd.load_cur_user_time(request, )
        # Local change here, to enable QSD editing.
        qsd.save()
        result['status'] = 1
        result['content'] = teximages(smartypants(markdown(qsd.content)))
        result['id'] = qsd.id
    if post_dict['cmd'] == "create":
        qsd_path = DataTree.objects.get(id=post_dict['anchor'])
        if not UserBit.UserHasPerms(request.user, qsd_path, EDIT_VERB):
            return HttpResponse(content="Sorry, you do not have permission to edit this page.", status=500)
        qsd, created = QuasiStaticData.objects.get_or_create(name=post_dict['name'],path=qsd_path,defaults={'author': request.user})
        qsd.content = post_dict['data']
        qsd.author = request.user
        qsd.save()
        result['status'] = 1
        result['content'] = teximages(smartypants(markdown(qsd.content)))
        result['id'] = qsd.id
    
    return HttpResponse(simplejson.dumps(result))
