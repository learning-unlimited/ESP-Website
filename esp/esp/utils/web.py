
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
import re
from django.template import Template, loader, RequestContext
from django.conf import settings
from django import http
from django.http import HttpResponse, HttpResponseRedirect
from esp.middleware import ESPError
from esp.themes.controllers import ThemeController
from esp.program.models import Program
from django.conf import settings
import django.shortcuts

def get_from_id(id, module, strtype = 'object', error = True):
    """ This function will get an object from its id, and return an appropriate error if need be. """
    from esp.users.models import ESPUser

    try:
        newid    = int(id)
        foundobj = module.objects.get(id = newid)
    except:
        if error:
            raise ESPError('Could not find the %s with id %s.' % (strtype, id), log=False)
        return None
    return foundobj

def render_to_response(template, request, context, content_type=None, use_request_context=True):
    from esp.web.views.navBar import makeNavBar

    if isinstance(template, (basestring,)):
        template = [ template ]

    section = request.path.split('/')[1]
    tc = ThemeController()
    context['theme'] = tc.get_template_settings()
    context['settings'] = settings

    context['current_programs'] = Program.current_programs()

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
def error404(request, template_name='404.html'):
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
    """
    def _wrapped_view(request, *args, **kwargs):
        if request.method == 'GET' and not request.is_secure():
            return HttpResponseRedirect(re.sub(r'^\w+://',
                                               r'https://',
                                               request.build_absolute_uri()))
        return view_fn(request, *args, **kwargs)
    return _wrapped_view

