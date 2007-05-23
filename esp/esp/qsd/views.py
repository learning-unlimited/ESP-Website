
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
from esp.datatree.models import GetNode, DataTree
from esp.web.views.navBar import makeNavBar
from esp.web.models import NavBarEntry
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
        START = 'nav_entry__'
        
        if not request.GET.has_key('ajax_movepage') or \
           not request.GET.has_key('seq'):
            return method(request, *args, **kwargs)
        
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
def qsd(request, branch, name, section, action):

    READ_VERB = 'V/Flags/Public'
    EDIT_VERB = 'V/Administer/Edit'

    # Pages are global per-user (not unique per-user)
    cache_id = '%s:%s' % (branch.id, name)

    if action == 'read':
        base_url = request.path[:-5]
    else:
        base_url = request.path[:(-len(action)-6)]

    # Detect edit authorizations
    have_edit = UserBit.UserHasPerms(request.user, branch, request.get_node(EDIT_VERB))

    if have_edit:
        have_read = True
    else:
        have_read = UserBit.UserHasPerms(request.user, branch, request.get_node(READ_VERB))

    if not have_read and action == 'read':
        raise Http403, "You do not have permission to access this page."

    # Fetch the QSD object
    try:
        cache_qsd = cache.get(urlencode('quasistaticdata:' + cache_id))
        
        if cache_qsd != None:
            qsd_rec = cache_qsd
        else:            
            qsd_recs = QuasiStaticData.objects.filter( path = branch, name = name ).order_by('-create_date')
            if qsd_recs.count() < 1:
                raise QuasiStaticData.DoesNotExist

            qsd_rec = qsd_recs[0]

            cache.set(urlencode('quasistaticdata:' + cache_id), qsd_rec)

    except QuasiStaticData.DoesNotExist:
        if have_edit:
            if action in ('edit','create',):
                qsd_rec = QuasiStaticData()
                qsd_rec.path = branch
                qsd_rec.name = name
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

        #cached_html = cache.get('quasistaticdata_html:' + cache_id)
        #if cached_html == None:
        cached_html = qsd_rec.html()
        #    cache.set('quasistaticdata_html:' + cache_id, cached_html)

        # Render response
        return render_to_response('qsd/qsd.html', request, (branch, section), {
            'title': qsd_rec.title,
            'content': cached_html,
            'qsdrec': qsd_rec,
            'have_edit': have_edit,
            'edit_url': base_url + ".edit.html" })

            
    # Detect POST
    if request.POST.has_key('post_edit'):
        if not have_edit:
            raise Http403, "Sorry, you do not have permission to edit this page."
        
        qsd_rec_new = QuasiStaticData()
        qsd_rec_new.path = branch
        qsd_rec_new.name = name
        qsd_rec_new.author = request.user
        qsd_rec_new.content = request.POST['content']
        qsd_rec_new.title = request.POST['title']
        qsd_rec_new.description = request.POST['description']
        qsd_rec_new.keywords    = request.POST['keywords']
        qsd_rec_new.save()

        qsd_rec = qsd_rec_new

        # If any files were uploaded, save them
        for FILE in request.FILES.keys():
            m = Media()

            # Strip "media/" from FILE, and strip the file name; just return the path
            path = dirname(FILE[6:])
            if path == '':
                m.anchor = qsd_rec.path
            else:
                m.anchor = GetNode('Q/' + dirname(FILE))
                
            m.mime_type = request.FILES[FILE]['content-type']
            # Do we want a better/manual mechanism for setting friendly_name?
            m.friendly_name = basename(FILE)
            m.size = len(request.FILES[FILE]['content'])
            
            splitname = basename(FILE).split('.')
            if len(splitname) > 1:
                m.file_extension = splitname[-1]
            else:
                m.file_extension = ''

            m.format = ''

            local_filename = FILE
            if FILE[:6] == 'media/':
                local_filename = FILE[6:]
                    
            m.save_target_file_file(local_filename, request.FILES[FILE]['content'])
            m.save()

        cache.delete(urlencode('quasistaticdata:' + cache_id))
        cache.delete(urlencode('quasistaticdata_html:' + cache_id))


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
            'qsdrec'       : qsd_rec,
            'qsd'          : True,
            'missing_files': m.BrokenLinks(),
            'target_url'   : base_url.split("/")[-1] + ".edit.html",
            'return_to_view': base_url.split("/")[-1] + ".html" })

    
    # Operation Complete!
    assert False, 'Unexpected QSD operation'
