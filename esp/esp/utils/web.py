
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
import os
import re
import zipfile
from io import BytesIO as StringIO
from django.template import Template, loader, RequestContext
from django.conf import settings
from django import http
from django.http import HttpResponse, HttpResponseRedirect
from esp.middleware import ESPError
from esp.themes.controllers import ThemeController
from esp.program.models import Program
from esp.web.views.navBar import makeNavBar
from esp.tagdict.models import Tag
import django.shortcuts

def get_from_id(id, module, strtype = 'object', error = True):
    """ This function will get an object from its id, and return an appropriate error if need be. """
    from esp.users.models import ESPUser

    try:
        newid    = int(id)
        foundobj = module.objects.get(id = newid)
    except (ValueError, TypeError, module.DoesNotExist):
        if error:
            raise ESPError(f'Could not find the {strtype} with id {id}.', log=False)
        return None
    return foundobj

def esp_context_stuff():
    context = {}

    tc = ThemeController()
    context['theme'] = tc.get_template_settings()
    context['current_theme_version'] = Tag.getTag("current_theme_version")
    context['current_logo_version'] = Tag.getTag("current_logo_version")
    context['current_header_version'] = Tag.getTag("current_header_version")
    context['current_favicon_version'] = Tag.getTag("current_favicon_version")
    context['settings'] = settings

    context['current_programs'] = Program.current_programs()
    return context

_PROGRAM_TLS = frozenset(['manage', 'learn', 'teach', 'onsite', 'volunteer'])

# Paths that must not trigger session/cookie access (NoVaryOnCookieTest).
# Accessing request.user would add Vary: Cookie; skip injection for these.
_CACHEABLE_SUFFIXES = ('catalog', 'index.html')


def _filter_active_tags(accessed_keys, get_all_fn):
    """
    Given the request-scoped set of consulted tag keys (or None if tracking
    wasn't initialized) and a callable that returns all non-default tags,
    return the list of tags that should appear in the banner.

    Returns [] if nothing should be shown so the caller can skip the DB hit
    in the empty-tracking case.
    """
    if accessed_keys is not None and not accessed_keys:
        # Tracking is active but the view consulted no tags — skip the DB
        # query entirely; nothing will be shown.
        return []
    all_nondefault = get_all_fn()
    if not all_nondefault:
        return []
    if accessed_keys is None:
        # Fallback: tracking wasn't initialized, show all non-default tags.
        return all_nondefault
    return [t for t in all_nondefault if t['key'] in accessed_keys]


def _inject_active_program_tags(request, context):
    """
    For admin users viewing a program page, inject ``active_program_tags``
    and ``active_global_tags`` (lists of tag info dicts) plus their
    corresponding settings URLs into *context* so the base template can
    show banners listing non-default tags actually consulted on this page.
    """
    try:
        path = request.path.rstrip('/')
        if any(path.endswith(s) for s in _CACHEABLE_SUFFIXES):
            return  # Avoid request.user access; would add Vary: Cookie
        if not (hasattr(request, 'user') and request.user.is_authenticated):
            return
        parts = request.path.strip('/').split('/')
        if len(parts) < 3:
            return
        tl, one, two = parts[0], parts[1], parts[2]
        if tl not in _PROGRAM_TLS:
            return
        from esp.program.models import Program
        try:
            program = Program.objects.get(url='%s/%s' % (one, two))
        except Program.DoesNotExist:
            return
        if not request.user.isAdministrator(program=program):
            return

        # Program-specific tags consulted while rendering this page.
        program_tags = _filter_active_tags(
            getattr(request, '_active_program_tag_keys', None),
            lambda: Tag.get_nondefault_program_tags(program),
        )
        if program_tags:
            context['active_program_tags'] = program_tags
            context['active_program_tags_url'] = program.get_manage_url() + 'tags'

        # Global tags consulted while rendering this page. Global tags affect
        # the whole site, so they're worth flagging in the same banner area
        # whenever an admin is on a program page that touched one.
        global_tags = _filter_active_tags(
            getattr(request, '_active_global_tag_keys', None),
            Tag.get_nondefault_global_tags,
        )
        if global_tags:
            context['active_global_tags'] = global_tags
            context['active_global_tags_url'] = '/manage/tags/'
    except Exception:
        pass  # Never let banner logic break page rendering


def render_to_response(template, request, context, content_type=None, use_request_context=True):
    if isinstance(template, str):
        template = [ template ]

    section = request.path.split('/')[1]

    context.update(esp_context_stuff())

    _inject_active_program_tags(request, context)

    # Shared base templates reference these optional values directly.
    # Default them here so pages that don't populate them don't emit
    # VariableDoesNotExist DEBUG noise during tests or local development.
    context.setdefault('login_result', '')
    context.setdefault('active_program_tags', [])
    context.setdefault('active_program_tags_url', '')
    context.setdefault('active_global_tags', [])
    context.setdefault('active_global_tags_url', '')

    # create nav bar list
    if not 'navbar_list' in context:
        category = None
        if 'nav_category' in context:
            category = context['nav_category']
        context['navbar_list'] = makeNavBar(section, category, path=request.path[1:])

    if use_request_context:
        context = RequestContext(request, context).flatten()
    return django.shortcuts.render(request, template, context, content_type=content_type)

""" Override Django error views to provide some context info. """
def error404(request, exception=None, template_name='404.html'):
    context = {'request_path': request.path}
    context['DEFAULT_EMAIL_ADDRESSES'] = settings.DEFAULT_EMAIL_ADDRESSES
    context['EMAIL_HOST_SENDER'] = settings.EMAIL_HOST_SENDER
    response = render_to_response(template_name, request, context)
    response.status_code = 404
    return response

def error500(request, template_name='500.html'):
    context = {}
    context['settings'] = settings # needed by elements/html
    context['DEFAULT_EMAIL_ADDRESSES'] = settings.DEFAULT_EMAIL_ADDRESSES
    context['EMAIL_HOST_SENDER'] = settings.EMAIL_HOST_SENDER
    context['request'] = request
    from datetime import datetime
    context['error_type'] = '500'
    context['error_title'] = 'Server Error'
    context['error_description'] = 'An unexpected server error occurred. Please try again in a moment.'
    context['error_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    context['error_url'] = request.build_absolute_uri()
    t = loader.get_template(template_name) # You need to create a 500.html template.

    # If possible, we want to render this page with our custom
    # render_to_response().  If this fails for some reason, we still want to
    # display the original 500 error page, so fall back to manually creating an
    # HttpResponse object.
    try:
        response = render_to_response(template_name, request, context)
        response.status_code = 500
        return response
    except Exception:
        # If possible, we want to render this page with a RequestContext so that
        # the context processors are run. If this fails for some reason, we still
        # want to display the original 500 error page, so fall back to using a
        # normal Context.
        try:
            return http.HttpResponseServerError(t.render(RequestContext(request, context).flatten()))
        except Exception:
            return http.HttpResponseServerError(t.render(context))

def secure_required(view_fn):
    """
    Apply this decorator to a view to require that the view only be accessed
    via a secure request. If the request is not secure, the wrapped view
    redirects to the https version of the uri. Otherwise it runs the view
    function as normal.

    The https redirect only occurs when the request method is GET, to avoid
    missing form submissions, even if they are insecure.

    When settings.DEBUG is True (i.e. on a development server), the redirect
    is skipped entirely, since dev servers typically cannot handle HTTPS.
    """
    def _wrapped_view(request, *args, **kwargs):
        if not settings.DEBUG and request.method == 'GET' and not request.is_secure():
            return HttpResponseRedirect(re.sub(r'^\w+://',
                                               r'https://',
                                               request.build_absolute_uri()))
        return view_fn(request, *args, **kwargs)
    return _wrapped_view

def zip_download(files = [], zipname = 'files'):
    """
    Zips a list of files together and returns it as a download
    """
    file_like = StringIO()
    zf = zipfile.ZipFile(file_like, 'w')
    for file in files:
        if file:
            zf.write(file, os.path.basename(os.path.normpath(file)))
    zf.close()
    response = HttpResponse(file_like.getvalue(), content_type='application/zip')
    response['Content-Disposition']=f'attachment; filename={zipname}.zip'
    return response
