
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
  Email: web-team@learningu.org
"""
from esp.qsd.models import QuasiStaticData
from esp.users.models import ContactInfo, Permission
from esp.web.models import NavBarEntry, NavBarCategory, default_navbarcategory
from esp.utils.web import render_to_response
from django.http import HttpResponse, Http404, HttpResponseNotAllowed, JsonResponse
from esp.qsdmedia.models import Media
from os.path import basename, dirname
from datetime import datetime
from django.core.cache import cache
from django.template.defaultfilters import urlencode
from esp.middleware import Http403
from esp.utils.no_autocookie import disable_csrf_cookie_update
from django.utils.cache import add_never_cache_headers, patch_cache_control, patch_vary_headers
from django.views.decorators.vary import vary_on_cookie
from django.views.decorators.cache import cache_control
from esp.varnish.varnish import purge_page
from urllib.parse import urlparse
from bleach import clean

from django.conf import settings
from django.views.decorators.http import require_POST

from reversion import revisions as reversion

# default edit permission
EDIT_PERM = 'V/Administer/Edit'

# spacing between separate nav bar entries
DEFAULT_SPACING = 5

#@vary_on_cookie
#@cache_control(max_age=180)    NOTE: patch_cache_control() below inserts cache header for view mode only
@disable_csrf_cookie_update
@reversion.create_revision()
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

    # Detect read authorizations
    have_read = True
    if url_parts[0] == 'manage' and not request.user.isAdministrator():
        have_read = False

    if not have_read and action == 'read':
        raise Http403("You do not have permission to access this page.")

    class_qsd = len(url_parts) > 3 and url_parts[3] == "Classes"

    # Fetch the QSD object
    try:
        qsd_rec = QuasiStaticData.objects.get_by_url(base_url)
        if qsd_rec is None:
            raise QuasiStaticData.DoesNotExist
        if qsd_rec.disabled:
            raise QuasiStaticData.DoesNotExist

    except QuasiStaticData.DoesNotExist:
        have_edit = Permission.user_can_edit_qsd(request.user, base_url)

        if have_edit:
            if action in ('edit', 'create',):
                qsd_rec = QuasiStaticData()
                qsd_rec.url = base_url
                qsd_rec.nav_category = default_navbarcategory()
                qsd_rec.title = 'New Page'
                qsd_rec.content = 'Please insert your text here'
                qsd_rec.create_date = datetime.now()
                qsd_rec.keywords = ''
                qsd_rec.description = ''
                action = 'edit'

            if (action == 'read'):
                edit_link = '/' + base_url + '.edit.html'
                response = render_to_response('qsd/nopage_create.html', request, {'edit_link': edit_link}, use_request_context=False)
                response.status_code = 404 # Make sure we actually 404, so that if there is a redirect the middleware can catch it.
                return response
        else:
            if action == 'read':
                raise Http404('This page does not exist.')
            else:
                raise Http403('Sorry, you can not modify <tt>%s</tt>.' % request.path)

    if action == 'create':
        action = 'edit'

    # Detect the standard read verb
    if action == 'read':

        # Render response
        response = render_to_response('qsd/qsd.html', request, {
            'title': qsd_rec.title,
            'nav_category': qsd_rec.nav_category,
            'content': qsd_rec.html(),
            'settings': settings,
            'qsdrec': qsd_rec,
            'class_qsd' : class_qsd,
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
    if 'post_edit' in request.POST:
        have_edit = Permission.user_can_edit_qsd(request.user, base_url)

        if not have_edit:
            raise Http403("Sorry, you do not have permission to edit this page.")

        nav_category_target = NavBarCategory.objects.get(id=request.POST['nav_category'])

        data = request.POST['content']
        if class_qsd:
            data = clean(data, strip = True)

        # Since QSD now uses reversion, we want to only modify the data if we've actually changed something
        # The revision will automatically be created upon calling the save function of the model object
        copy_map = {
            'url': base_url,
            'nav_category': nav_category_target,
            'content': data,
            'title': request.POST['title'],
            'description': request.POST['description'],
            'keywords': request.POST['keywords'],
        }
        diff_found = False
        for field, new_value in copy_map.items():
            if getattr(qsd_rec, field) != new_value:
                setattr(qsd_rec, field, new_value)
                diff_found = True

        if diff_found:
            qsd_rec.load_cur_user_time(request)
            reversion.set_user(request.user)
            qsd_rec.save()

            # We should also purge the cache
            purge_page(qsd_rec.url+".html")


    # Detect the edit verb
    if action == 'edit':
        have_edit = Permission.user_can_edit_qsd(request.user, base_url)

        # Enforce authorizations (FIXME: SHOW A REAL ERROR!)
        if not have_edit:
            raise Http403("You don't have permission to edit this page.")

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
            'class_qsd'    : class_qsd,
            'target_url'   : base_url.split("/")[-1] + ".edit.html",
            'return_to_view': base_url.split("/")[-1] + ".html#refresh" },
            use_request_context=False)

    # Operation Complete!
    raise Http404('Unexpected QSD operation')

@reversion.create_revision()
def ajax_qsd(request):
    """ Ajax function for in-line QSD editing.  """
    import json
    from markdown import markdown

    result = {}
    post_dict = request.POST.copy()

    if ( request.user.id is None ):
        return HttpResponse(content='Oops! Your session expired!\nPlease open another window, log in, and try again.\nYour changes will not be lost if you keep this page open.', status=401)
    if post_dict['cmd'] == "update":
        if not Permission.user_can_edit_qsd(request.user, post_dict['url']):
            return HttpResponse(content='Sorry, you do not have permission to edit this page.', status=403)

        qsd, created = QuasiStaticData.objects.get_or_create(url=post_dict['url'], defaults={'author': request.user})

        # Clobber prevention. -ageng 2013-08-12
        # Now needs to be slightly more complicated since we're on reversion. -ageng 2014-01-04
        if not QuasiStaticData.objects.get_by_url(qsd.url) == qsd:
            return HttpResponse(content='The edit you are submitting is not based on the newest version!\n(Is someone else editing? Did you get here by a back button?)\nCopy out your work if you need it. Then refresh the page to get the latest version.', status=409)

        data = post_dict['data']

        # Get the URL from the request information
        referer = request.META.get('HTTP_REFERER')
        path = urlparse(referer).path
        path_parts = [el for el in path.split('/') if el != '']

        # Sanitize if this is for a class QSD
        if len(path_parts) > 3 and path_parts[3] == "Classes":
            data = clean(data, strip = True)

        # Since QSD now uses reversion, we want to only modify the data if we've actually changed something
        # The revision will automatically be created upon calling the save function of the model object
        if qsd.content != data:
            qsd.content = data
            qsd.load_cur_user_time(request, )
            reversion.set_user(request.user)
            qsd.save()

            # We should also purge the cache
            purge_page(qsd.url+".html")

        result['status'] = 1
        result['content'] = markdown(qsd.content)
        result['url'] = qsd.url

    return HttpResponse(json.dumps(result))

def ajax_qsd_preview(request):
    """ Ajax function for previewing the result of QSD editing. """
    import json
    from markdown import markdown
    data = request.POST['data']

    # Get the URL from the request information
    referer = request.META.get('HTTP_REFERER')
    path = urlparse(referer).path
    path_parts = [el for el in path.split('/') if el != '']

    # Sanitize if this is for a class QSD
    if len(path_parts) > 3 and path_parts[3] == "Classes":
        data = clean(data, strip = True)

    # We don't necessarily need to wrap it in JSON, but this seems more
    # future-proof.
    result = {'content': markdown(data)}

    return HttpResponse(json.dumps(result))


def ajax_qsd_history(request):
    """ Return JSON list of versions for a QSD URL. """
    import json
    from reversion.models import Version
    from django.contrib.contenttypes.models import ContentType
    from esp.users.models import ESPUser

    qsd_url = request.GET.get('url', '')
    if not qsd_url:
        return JsonResponse({'error': 'Missing url parameter'}, status=400)

    if not Permission.user_can_edit_qsd(request.user, qsd_url):
        return HttpResponse('Permission denied', status=403)

    qsd_objects = QuasiStaticData.objects.filter(url=qsd_url)
    if not qsd_objects.exists():
        return JsonResponse({'versions': []})

    ct = ContentType.objects.get_for_model(QuasiStaticData)
    object_ids = [str(pk) for pk in qsd_objects.values_list('pk', flat=True)]
    versions = Version.objects.filter(
        content_type=ct,
        object_id__in=object_ids,
    ).select_related('revision').order_by('-revision__date_created')[:50]

    # Bulk-fetch all user IDs we'll need to resolve usernames (avoids N+1)
    user_ids = set()
    version_data = []
    for v in versions:
        field_dict = v.field_dict
        rev = v.revision
        if rev.user_id:
            user_ids.add(rev.user_id)
        if 'author' in field_dict:
            try:
                user_ids.add(int(field_dict['author']))
            except (ValueError, TypeError):
                pass
        version_data.append((v, field_dict, rev))

    user_map = {}
    if user_ids:
        user_map = dict(ESPUser.objects.filter(pk__in=user_ids).values_list('pk', 'username'))

    result = []
    for v, field_dict, rev in version_data:
        user_name = ''
        if rev.user_id:
            user_name = user_map.get(rev.user_id, 'Unknown')
        if not user_name and 'author' in field_dict:
            try:
                user_name = user_map.get(int(field_dict['author']), 'Unknown')
            except (ValueError, TypeError):
                user_name = 'Unknown'

        content = field_dict.get('content', '')
        snippet = content[:150].replace('\n', ' ').strip()
        if len(content) > 150:
            snippet += '...'

        result.append({
            'version_id': v.pk,
            'date': rev.date_created.strftime('%b %d, %Y %I:%M %p'),
            'author': user_name,
            'title': field_dict.get('title', ''),
            'snippet': snippet,
        })

    return JsonResponse({'versions': result})


def ajax_qsd_version_preview(request):
    """ Return rendered content for a specific version. """
    import json
    from reversion.models import Version
    from django.contrib.contenttypes.models import ContentType
    from markdown import markdown

    version_id = request.GET.get('version_id', '')
    if not version_id:
        return JsonResponse({'error': 'Missing version_id'}, status=400)

    ct = ContentType.objects.get_for_model(QuasiStaticData)
    try:
        version = Version.objects.select_related('revision').get(pk=version_id, content_type=ct)
    except Version.DoesNotExist:
        return HttpResponse('Version not found', status=404)

    field_dict = version.field_dict
    qsd_url = field_dict.get('url', '')

    if not Permission.user_can_edit_qsd(request.user, qsd_url):
        return HttpResponse('Permission denied', status=403)

    content = field_dict.get('content', '')
    result = {
        'content_raw': content,
        'content_html': markdown(content),
        'title': field_dict.get('title', ''),
    }
    return JsonResponse(result)


@require_POST
@reversion.create_revision()
def ajax_qsd_restore(request):
    """ Restore a QSD to a specific historical version. """
    import json
    from reversion.models import Version
    from django.contrib.contenttypes.models import ContentType
    from markdown import markdown

    if request.user.id is None:
        return HttpResponse('Session expired', status=401)

    version_id = request.POST.get('version_id', '')
    if not version_id:
        return JsonResponse({'error': 'Missing version_id'}, status=400)

    ct = ContentType.objects.get_for_model(QuasiStaticData)
    try:
        version = Version.objects.select_related('revision').get(pk=version_id, content_type=ct)
    except Version.DoesNotExist:
        return HttpResponse('Version not found', status=404)

    field_dict = version.field_dict
    qsd_url = field_dict.get('url', '')

    if not Permission.user_can_edit_qsd(request.user, qsd_url):
        return HttpResponse('Permission denied', status=403)

    qsd_obj = QuasiStaticData.objects.get_by_url(qsd_url)
    if qsd_obj is None:
        return HttpResponse('QSD not found', status=404)

    qsd_obj.content = field_dict.get('content', '')
    qsd_obj.title = field_dict.get('title', qsd_obj.title)
    if 'nav_category' in field_dict:
        qsd_obj.nav_category_id = field_dict['nav_category']
    if 'keywords' in field_dict:
        qsd_obj.keywords = field_dict['keywords']
    if 'description' in field_dict:
        qsd_obj.description = field_dict['description']

    qsd_obj.load_cur_user_time(request)
    reversion.set_user(request.user)
    reversion.set_comment('Restored from version %s' % version_id)
    qsd_obj.save()

    purge_page(qsd_obj.url + ".html")

    result = {
        'status': 1,
        'content': markdown(qsd_obj.content),
        'url': qsd_obj.url,
    }
    return JsonResponse(result)
