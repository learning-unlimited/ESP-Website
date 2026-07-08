
from __future__ import absolute_import
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
from esp.qsd.models import QuasiStaticData, QSDConflict, edit_history, version_snapshot
from esp.users.models import ContactInfo, Permission
from esp.web.models import NavBarEntry, NavBarCategory, default_navbarcategory
from esp.utils.web import render_to_response
from django.http import HttpResponse, HttpResponseRedirect, Http404, HttpResponseNotAllowed
from esp.qsdmedia.models import Media
from os.path import basename, dirname
from datetime import datetime
from django.core.cache import cache
from django.template.defaultfilters import urlencode
from esp.middleware import Http403
from esp.utils.no_autocookie import disable_csrf_cookie_update
from django.utils.cache import add_never_cache_headers, patch_cache_control, patch_vary_headers
from django.utils.formats import date_format
from django.views.decorators.vary import vary_on_cookie
from django.views.decorators.cache import cache_control
from esp.varnish.varnish import purge_page
from urllib.parse import urlparse
from bleach import clean
from markdown import markdown
import json

from django.conf import settings

from reversion import revisions as reversion

# default edit permission
EDIT_PERM = 'V/Administer/Edit'

# spacing between separate nav bar entries
DEFAULT_SPACING = 5

def _qsd_conflict_payload(conflict):
    """
    Builds the {'message', 'orig_id', 'orig_version'} payload used for
    ajax_qsd's 'update' command on a QSDConflict -- refreshed to the current
    state, so that a deliberate resubmit (after the user has seen the
    conflict) is a real override rather than resubmitting the same stale
    tokens and hitting the same conflict again.
    """
    # Worded to match the full-page editor's conflict banner
    # (qsd/qsd_edit.html) as closely as the different medium allows -- same
    # explanation, same "click X again to overwrite" framing, same button
    # label as the one this block's Save button actually shows.
    message = ('This content was changed by someone else after you started editing it. '
                'Your changes here have not been saved -- review the content against the '
                'latest version, then click "Save changes" again to overwrite it, or reload '
                'the page to discard your changes and see the latest version instead.')
    if conflict.history:
        message += '\n\nRecent edits:\n' + '\n'.join(
            '%s -- %s' % (h['user'], date_format(h['date'], 'DATETIME_FORMAT'))
            for h in conflict.history)
    current = conflict.current
    return {
        'message': message,
        'orig_id': current.pk if current is not None else '',
        'orig_version': current.latest_version_id() if current is not None else '',
    }

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

    # Fetch the QSD object. A disabled QSD is treated the same as a missing
    # one for display purposes. If we're about to (re)create it, reuse the
    # existing row and re-enable it rather than making a new one -- url is
    # unique, so a second row at the same url isn't possible -- and start the
    # editor from the same blank/default content used for a truly new page,
    # not the disabled row's old content.
    qsd_rec = QuasiStaticData.objects.get_by_url(base_url)
    if qsd_rec is None or qsd_rec.disabled:
        have_edit = Permission.user_can_edit_qsd(request.user, base_url)

        if have_edit:
            if action in ('edit', 'create',):
                if qsd_rec is None:
                    qsd_rec = QuasiStaticData()
                    qsd_rec.url = base_url
                else:
                    qsd_rec.disabled = False
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
        # max_age=0 forces every browser to revalidate with the origin (via
        # Varnish) on every visit, rather than silently serving a stale local
        # copy for up to an hour after an edit. s_maxage keeps Varnish's own
        # cache long-lived; purge_page() actively invalidates it on save, so
        # revalidation is normally a fast Varnish hit, not a full DB read.
        patch_cache_control(response, public=True, max_age=0, s_maxage=3600)

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
        diff_found = qsd_rec.disabled or any(
            getattr(qsd_rec, field) != new_value for field, new_value in copy_map.items())

        if diff_found:
            orig_id = int(request.POST['orig_id']) if request.POST.get('orig_id') else None
            orig_version = int(request.POST['orig_version']) if request.POST.get('orig_version') else None

            def populate(rec):
                for field, new_value in copy_map.items():
                    setattr(rec, field, new_value)
                rec.disabled = False
                rec.load_cur_user_time(request)

            try:
                qsd_rec = QuasiStaticData.objects.save_with_conflict_check(
                    base_url, orig_id, orig_version, populate)
            except QSDConflict as conflict:
                # Someone else created, deleted, or edited this page since we
                # started editing it. Redisplay the form with our submitted
                # changes intact (rather than losing them), along with who
                # changed it and when, and fresh orig_id/orig_version so a
                # deliberate resubmit compares against the new current state.
                current = conflict.current
                return render_to_response('qsd/qsd_edit.html', request, {
                    'conflict'     : True,
                    'edit_history' : conflict.history,
                    'title'        : request.POST['title'],
                    'content'      : request.POST['content'],
                    'keywords'     : request.POST['keywords'],
                    'description'  : request.POST['description'],
                    'nav_category' : nav_category_target,
                    'nav_categories': NavBarCategory.objects.all(),
                    'qsdrec'       : current,
                    'orig_id'      : current.pk if current is not None else None,
                    'orig_version' : current.latest_version_id() if current is not None else None,
                    'qsd'          : True,
                    'class_qsd'    : class_qsd,
                    'target_url'   : base_url.split("/")[-1] + ".edit.html",
                    'history_url'  : base_url.split("/")[-1] + ".history.html",
                    'return_to_view': base_url.split("/")[-1] + ".html#refresh" },
                    use_request_context=False)

            # We should also purge the cache
            purge_page(qsd_rec.url+".html")

            # Redirect back to the edit page rather than re-rendering it
            # directly. This request's revision hasn't been persisted yet
            # (qsd() is itself wrapped in @reversion.create_revision(), so
            # the just-created Version isn't visible to
            # qsd_rec.latest_version_id() until this whole view returns) --
            # re-rendering inline would bake a stale orig_version into the
            # form, causing the *next* edit to spuriously conflict with
            # itself. A fresh GET on redirect sees the fully-persisted
            # version.
            return HttpResponseRedirect(request.path)

    if 'post_revert' in request.POST:
        have_edit = Permission.user_can_edit_qsd(request.user, base_url)

        if not have_edit:
            raise Http403("Sorry, you do not have permission to edit this page.")

        version_id = int(request.POST['version_id'])
        orig_id = int(request.POST['orig_id']) if request.POST.get('orig_id') else None
        orig_version = int(request.POST['orig_version']) if request.POST.get('orig_version') else None

        # Scoped to qsd_rec's own history -- can only ever restore content
        # that really was this row's content at some point, not an
        # arbitrary version pk belonging to some other QSD.
        snapshot = version_snapshot(qsd_rec, version_id)
        if snapshot is None:
            raise Http404("That version is no longer available for this page.")

        def populate(rec):
            rec.title = snapshot.title
            rec.content = snapshot.content
            rec.keywords = snapshot.keywords
            rec.description = snapshot.description
            rec.nav_category_id = snapshot.nav_category_id
            rec.disabled = False
            rec.load_cur_user_time(request)

        try:
            qsd_rec = QuasiStaticData.objects.save_with_conflict_check(
                base_url, orig_id, orig_version, populate)
        except QSDConflict as conflict:
            # Same idea as the post_edit conflict handling above: someone
            # else changed the page since the history page was loaded.
            # Redisplay history against the current state rather than
            # silently reverting over their edit.
            current = conflict.current
            return render_to_response('qsd/qsd_history.html', request, {
                'conflict'     : True,
                'qsdrec'       : current,
                'history'      : edit_history(current, limit=None) if current is not None else [],
                'preview'      : None,
                'orig_id'      : current.pk if current is not None else None,
                'orig_version' : current.latest_version_id() if current is not None else None,
                'qsd'          : True,
                'class_qsd'    : class_qsd,
                'target_url'   : base_url.split("/")[-1] + ".edit.html",
                'history_url'  : base_url.split("/")[-1] + ".history.html",
                'return_to_view': base_url.split("/")[-1] + ".html#refresh" },
                use_request_context=False)

        # We should also purge the cache
        purge_page(qsd_rec.url+".html")

        # Redirect back to the history page rather than re-rendering it
        # directly, for the same "read your own write" reason as post_edit
        # above -- the revision from this request isn't persisted yet.
        return HttpResponseRedirect(request.path)

    # Detect the history verb
    if action == 'history':
        have_edit = Permission.user_can_edit_qsd(request.user, base_url)

        if not have_edit:
            raise Http403("You don't have permission to view this page's history.")

        if qsd_rec is None:
            raise Http404("This page doesn't exist yet, so it has no history.")

        # Optional read-only preview of one past version, so an admin can
        # look at a version's actual rendered content before deciding to
        # revert to it -- no DB write, just a rendering of that version's
        # snapshot.
        preview = None
        preview_param = request.GET.get('preview')
        if preview_param:
            try:
                preview_version_id = int(preview_param)
            except ValueError:
                raise Http404("Invalid version.")
            snapshot = version_snapshot(qsd_rec, preview_version_id)
            if snapshot is None:
                raise Http404("That version is no longer available for this page.")
            preview = {
                'version_id': preview_version_id,
                'title': snapshot.title,
                'content': markdown(snapshot.content),
                'user': snapshot.author,
                'date': snapshot.create_date,
            }

        return render_to_response('qsd/qsd_history.html', request, {
            'qsdrec'       : qsd_rec,
            'history'      : edit_history(qsd_rec, limit=None),
            'preview'      : preview,
            'orig_id'      : qsd_rec.pk,
            'orig_version' : qsd_rec.latest_version_id(),
            'qsd'          : True,
            'class_qsd'    : class_qsd,
            'target_url'   : base_url.split("/")[-1] + ".edit.html",
            'history_url'  : base_url.split("/")[-1] + ".history.html",
            'return_to_view': base_url.split("/")[-1] + ".html#refresh" },
            use_request_context=False)

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
            'orig_id'      : qsd_rec.pk,
            'orig_version' : qsd_rec.latest_version_id(),
            'qsd'          : True,
            'class_qsd'    : class_qsd,
            'target_url'   : base_url.split("/")[-1] + ".edit.html",
            'history_url'  : base_url.split("/")[-1] + ".history.html",
            'return_to_view': base_url.split("/")[-1] + ".html#refresh" },
            use_request_context=False)

    # Operation Complete!
    raise Http404('Unexpected QSD operation')

@reversion.create_revision()
def ajax_qsd(request):
    """ Ajax function for in-line QSD editing.  """
    result = {}
    post_dict = request.POST.copy()

    if ( request.user.id is None ):
        return HttpResponse(content='Oops! Your session expired!\nPlease open another window, log in, and try again.\nYour changes will not be lost if you keep this page open.', status=401)
    if post_dict['cmd'] == "update":
        if not Permission.user_can_edit_qsd(request.user, post_dict['url']):
            return HttpResponse(content='Sorry, you do not have permission to edit this page.', status=403)

        data = post_dict['data']

        # Get the URL from the request information
        referer = request.META.get('HTTP_REFERER')
        path = urlparse(referer).path
        path_parts = [el for el in path.split('/') if el != '']

        # Santize if this is for a class QSD
        if len(path_parts) > 3 and path_parts[3] == "Classes":
            data = clean(data, strip = True)

        orig_id = int(post_dict['orig_id']) if post_dict.get('orig_id') else None
        orig_version = int(post_dict['orig_version']) if post_dict.get('orig_version') else None

        # Editing a disabled block re-enables it -- otherwise the block would
        # keep rendering as if empty even after being "edited".
        def populate(rec):
            rec.content = data
            rec.disabled = False
            rec.load_cur_user_time(request)

        try:
            qsd = QuasiStaticData.objects.save_with_conflict_check(
                post_dict['url'], orig_id, orig_version, populate)
        except QSDConflict as conflict:
            return HttpResponse(content=json.dumps(_qsd_conflict_payload(conflict)),
                                 status=409, content_type='application/json')

        # We should also purge the cache
        purge_page(qsd.url+".html")

        result['status'] = 1
        result['content'] = markdown(qsd.content)
        result['url'] = qsd.url

    elif post_dict['cmd'] == 'check_fresh':
        # Non-destructive: lets the client warn an editor, before they start
        # typing, that their starting point is already out of date -- rather
        # than only finding out when they try to save. Also returns the
        # actual current content, so the client can additionally compare it
        # against what's actually sitting in the textarea -- catches the
        # case where the browser silently restored a stale <textarea> value
        # across a plain page refresh (a browser form-state quirk, not a
        # server caching issue) even though orig_id/orig_version (plain div
        # attributes, not form controls, so not subject to that restore
        # behavior) look perfectly fresh and wouldn't trip check_freshness
        # on their own.
        orig_id = int(post_dict['orig_id']) if post_dict.get('orig_id') else None
        orig_version = int(post_dict['orig_version']) if post_dict.get('orig_version') else None
        current = QuasiStaticData.objects.get_by_url(post_dict['url'])
        stale, history = QuasiStaticData.objects.check_freshness(post_dict['url'], orig_id, orig_version)
        result['stale'] = stale
        result['content'] = current.content if current is not None else ''
        result['history'] = [
            {'user': str(h['user']), 'date': date_format(h['date'], 'DATETIME_FORMAT')} for h in history
        ]

    elif post_dict['cmd'] == 'history':
        # Full version list for the inline "History" panel. Requires edit
        # permission -- same bar as actually changing the page.
        if not Permission.user_can_edit_qsd(request.user, post_dict['url']):
            return HttpResponse(content='Sorry, you do not have permission to edit this page.', status=403)

        qsd_obj = QuasiStaticData.objects.get_by_url(post_dict['url'])
        result['history'] = [
            {'version_id': h['version_id'], 'user': str(h['user']), 'date': date_format(h['date'], 'DATETIME_FORMAT')}
            for h in edit_history(qsd_obj, limit=None)
        ]

    elif post_dict['cmd'] == 'preview_version':
        # Non-destructive: fetches one past version's raw content without
        # touching the database, so the inline editor can load it straight
        # into the textarea (and the Jodit/TinyMDE widget bound to it) for
        # the user to review -- and possibly toggle to HTML source view,
        # tweak, etc -- before deciding whether to click the ordinary "Save
        # changes" button, which reverts it via the normal, fully
        # conflict-checked update path. No separate revert command needed.
        if not Permission.user_can_edit_qsd(request.user, post_dict['url']):
            return HttpResponse(content='Sorry, you do not have permission to edit this page.', status=403)

        qsd_obj = QuasiStaticData.objects.get_by_url(post_dict['url'])
        snapshot = version_snapshot(qsd_obj, int(post_dict['version_id']))
        if snapshot is None:
            return HttpResponse(content='That version is no longer available for this page.', status=404)

        result['content'] = snapshot.content
        result['user'] = str(snapshot.author)
        result['date'] = date_format(snapshot.create_date, 'DATETIME_FORMAT')

    return HttpResponse(json.dumps(result))

def ajax_qsd_preview(request):
    """ Ajax function for previewing the result of QSD editing. """
    data = request.POST['data']

    # Get the URL from the request information
    referer = request.META.get('HTTP_REFERER')
    path = urlparse(referer).path
    path_parts = [el for el in path.split('/') if el != '']

    # Santize if this is for a class QSD
    if len(path_parts) > 3 and path_parts[3] == "Classes":
        data = clean(data, strip = True)

    # We don't necessarily need to wrap it in JSON, but this seems more
    # future-proof.
    result = {'content': markdown(data)}

    return HttpResponse(json.dumps(result))
