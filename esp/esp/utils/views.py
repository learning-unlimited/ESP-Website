from __future__ import absolute_import
from io import open
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

from esp.utils.web import render_to_response
from esp.utils.models import TemplateOverride
from esp.users.models import admin_required
from difflib import HtmlDiff
import os.path
from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden

@admin_required
def diff_templateoverride(request, template_id):
    template_dir = os.path.join(settings.PROJECT_ROOT, 'templates')
    qs = TemplateOverride.objects.filter(id=template_id)
    if qs.exists():
        override_obj = qs.order_by('-version')[0]
    else:
        raise Http404

    override_lines = override_obj.content.split('\n')

    original_path = os.path.join(template_dir, override_obj.name)
    with open(original_path) as original_file:
        original_lines = list(original_file)

    context = {}
    context['name'] = override_obj.name
    context['version'] = override_obj.version
    context['diff'] = HtmlDiff().make_table(
            original_lines, override_lines,
            'original', 'override (version {})'.format(template_id))
    return render_to_response('utils/diff_templateoverride.html', request, context)


@admin_required
def test_error(request, code):
    code = int(code)
    if code == 200:
        return HttpResponse("OK - no error triggered")
    elif code == 400:
        return HttpResponseBadRequest("Test 400 error - triggered manually via /manage/testerror/400")
    elif code == 401:
        return HttpResponse("Test 401 error - triggered manually via /manage/testerror/401", status=401)
    elif code == 403:
        return HttpResponseForbidden("Test 403 error - triggered manually via /manage/testerror/403")
    elif code == 404:
        raise Http404("Test 404 error - triggered manually via /manage/testerror/404")
    elif code == 500:
        raise Exception("Test error - triggered manually via /manage/testerror/500")
    else:
        raise Http404("Unsupported test error code %d" % code)
