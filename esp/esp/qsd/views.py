
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@lists.learningu.org
"""
from esp.qsd.models import QuasiStaticData
from django.contrib.auth.models import User
from esp.users.models import ContactInfo, Permission
from esp.datatree.models import *
from esp.web.views.navBar import makeNavBar
from esp.web.models import NavBarEntry, NavBarCategory
from esp.web.util.main import render_to_response
from django.http import HttpResponse, Http404, HttpResponseNotAllowed
from esp.qsdmedia.models import Media
from esp.lib.markdownaddons import ESPMarkdown
from os.path import basename, dirname
from datetime import datetime
from django.core.cache import cache
from django.template.defaultfilters import urlencode
from esp.middleware import ESPError, Http403
from esp.utils.no_autocookie import disable_csrf_cookie_update
from django.utils.cache import add_never_cache_headers, patch_cache_control, patch_vary_headers
from django.views.decorators.vary import vary_on_cookie
from django.views.decorators.cache import cache_control
from esp.cache.varnish import purge_page

from django.conf import settings

# default edit permission
EDIT_PERM = 'V/Administer/Edit'

# spacing between separate nav bar entries
DEFAULT_SPACING = 5

#@vary_on_cookie
#@cache_control(max_age=180)    NOTE: patch_cache_control() below inserts cache header for view mode only
@disable_csrf_cookie_update
def qsd(request, url):

    #   Extract the 'action' from the supplied URL if there is one
    url_parts = url.split('/')
    page_name = url_parts[-1]
    page_name_parts = page_name.split('.')
    if len(page_name_parts) > 1:
        action = page_name_parts[-1]
        page_name_base = '.'.join(page_name_parts[:-1])
    else:
        action = 'read'
        page_name_base = page_name
    base_url = '/'.join(url_parts[:-1] + [page_name_base])
    
    # Detect edit authorizations
    have_read = True
    
    if not have_read and action == 'read':
        raise Http403, "You do not have permission to access this page."

    # Fetch the QSD object
    try:
        qsd_rec = QuasiStaticData.objects.get_by_url(base_url)
        if qsd_rec == None:
            raise QuasiStaticData.DoesNotExist
        if qsd_rec.disabled:
            raise QuasiStaticData.DoesNotExist

    except QuasiStaticData.DoesNotExist:
        have_edit = Permission.user_can_edit_qsd(request.user, base_url)

        if have_edit:
            if action in ('edit','create',):
                qsd_rec = QuasiStaticData()
                qsd_rec.url = base_url
                qsd_rec.nav_category = NavBarCategory.default()
                qsd_rec.title = 'New Page'
                qsd_rec.content = 'Please insert your text here'
                qsd_rec.create_date = datetime.now()
                qsd_rec.keywords = ''
                qsd_rec.description = ''
                action = 'edit'

            if (action == 'read'):
                edit_link = '/' + base_url + '.edit.html'
                return render_to_response('qsd/nopage_create.html', request, {'edit_link': edit_link}, use_request_context=False)  
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
        response = render_to_response('qsd/qsd.html', request, {
            'title': qsd_rec.title,
            'nav_category': qsd_rec.nav_category, 
            'content': qsd_rec.html(),
            'settings': settings,
            'qsdrec': qsd_rec,
            'have_edit': True,  ## Edit-ness is determined client-side these days
            'edit_url': '/' + base_url + ".edit.html" }, use_request_context=False)

#        patch_vary_headers(response, ['Cookie'])
#        if have_edit:
#            add_never_cache_headers(response)
#            patch_cache_control(response, no_cache=True, no_store=True)
#        else:
        patch_cache_control(response, max_age=3600, public=True)

        return response

            
    # Detect POST
    if request.POST.has_key('post_edit'):
        have_edit = Permission.user_can_edit_qsd(request.user, base_url)

        if not have_edit:
            raise Http403, "Sorry, you do not have permission to edit this page."
        
        nav_category_target = NavBarCategory.objects.get(id=request.POST['nav_category'])

        # Since QSD now uses reversion, we want to only modify the data if we've actually changed something
        # The revision will automatically be created upon calling the save function of the model object
        if qsd_rec.url != base_url or qsd_rec.nav_category != nav_category_target or qsd_rec.content != request.POST['content'] or qsd_rec.description != request.POST['description'] or qsd_rec.keywords != request.POST['keywords']:
            qsd_rec.url = base_url
            qsd_rec.nav_category = NavBarCategory.objects.get(id=request.POST['nav_category'])
            qsd_rec.content = request.POST['content']
            qsd_rec.title = request.POST['title']
            qsd_rec.description = request.POST['description']
            qsd_rec.keywords    = request.POST['keywords']

            qsd_rec.load_cur_user_time(request)
            qsd_rec.save()

            # We should also purge the cache
            purge_page(qsd_rec.url+".html")

        # If any files were uploaded, save them
        for name, file in request.FILES.iteritems():
            m = Media()

            # Strip "media/" from FILE, and strip the file name; just return the path
            path = dirname(name[9:])
                
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
        have_edit = Permission.user_can_edit_qsd(request.user, base_url)

        # Enforce authorizations (FIXME: SHOW A REAL ERROR!)
        if not have_edit:
            raise ESPError(False), "You don't have permission to edit this page."

        m = ESPMarkdown(qsd_rec.content, media={})

        m.toString()
#        assert False, m.BrokenLinks()
        
        # Render an edit form
        return render_to_response('qsd/qsd_edit.html', request, {
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
            'return_to_view': base_url.split("/")[-1] + ".html#refresh" },  
            use_request_context=False)  
    
    # Operation Complete!
    raise Http404('Unexpected QSD operation')

def ajax_qsd(request):
    """ Ajax function for in-line QSD editing.  """
    from django.utils import simplejson
    from esp.lib.templatetags.markdown import markdown

    result = {}
    post_dict = request.POST.copy()

    if ( request.user.id is None ):
        return HttpResponse(content='Oops! Your session expired!\nPlease open another window, log in, and try again.\nYour changes will not be lost if you keep this page open.', status=500)
    if post_dict['cmd'] == "update":
        qsd = QuasiStaticData.objects.get(id=post_dict['id'])
        if not Permission.user_can_edit_qsd(request.user, qsd.url):
            return HttpResponse(content='Sorry, you do not have permission to edit this page.', status=500)

        # Since QSD now uses reversion, we want to only modify the data if we've actually changed something
        # The revision will automatically be created upon calling the save function of the model object
        if qsd.content != post_dict['data']:
            qsd.content = post_dict['data']
            qsd.load_cur_user_time(request, )
            qsd.save()

            # We should also purge the cache
            purge_page(qsd.url+".html")

        result['status'] = 1
        result['content'] = markdown(qsd.content)
        result['id'] = qsd.id
    if post_dict['cmd'] == "create":
        if not Permission.user_can_edit_qsd(request.user, post_dict['url']):
            return HttpResponse(content="Sorry, you do not have permission to edit this page.", status=500)
        qsd, created = QuasiStaticData.objects.get_or_create(url=post_dict['url'],defaults={'author': request.user})
        qsd.content = post_dict['data']
        qsd.author = request.user
        qsd.save()
        result['status'] = 1
        result['content'] = markdown(qsd.content)
        result['id'] = qsd.id
    
    return HttpResponse(simplejson.dumps(result))
