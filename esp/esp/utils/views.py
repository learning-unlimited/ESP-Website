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
from django.http import Http404, JsonResponse

@admin_required
def get_default_template_content(request):
    """Return the on-disk content of a default template as JSON, for use by
    the admin "Load default template" button on the TemplateOverride add form.

    GET parameter:
        name -- relative path of the template (e.g. "program/receipt.html")

    Responds with JSON:
        {"content": "..."} on success
        {"error": "..."} on failure (with an appropriate HTTP status code)
    """
    name = request.GET.get('name', '').strip()
    if not name:
        return JsonResponse({'error': 'No template name provided.'}, status=400)

    template_dir = os.path.realpath(os.path.join(settings.PROJECT_ROOT, 'templates'))
    requested_path = os.path.realpath(os.path.join(template_dir, name))

    # Guard against path traversal (e.g. "../../etc/passwd")
    if not requested_path.startswith(template_dir + os.sep):
        return JsonResponse({'error': 'Invalid template name.'}, status=400)

    if not os.path.isfile(requested_path):
        return JsonResponse({'error': 'Template not found: %s' % name}, status=404)

    with open(requested_path) as f:
        content = f.read()

    return JsonResponse({'content': content})


def _normalize_lines_for_diff(text):
    """Normalize text to a list of lines without trailing newlines for reliable diff.

    Uses splitlines() so that both file content and DB content are compared
    the same way. This avoids the bug where original lines had '\\n' (from
    list(file)) and override lines did not (from content.split('\\n')), making
    every line appear changed.
    """
    if text is None:
        return []
    return text.splitlines()


@admin_required
def diff_templateoverride(request, template_id):
    template_dir = os.path.join(settings.PROJECT_ROOT, 'templates')
    template_dir_real = os.path.realpath(template_dir)
    qs = TemplateOverride.objects.filter(id=template_id)
    if qs.exists():
        override_obj = qs.order_by('-version')[0]
    else:
        raise Http404

    # Use normalized lines (no trailing newlines) so the diff compares logical
    # lines and does not show the whole file as changed due to line-ending mismatch.
    override_lines = _normalize_lines_for_diff(override_obj.content)

    original_path = os.path.join(template_dir_real, override_obj.name)
    original_real = os.path.realpath(original_path)
    # Prevent directory traversal: ensure the resolved path stays within template_dir_real
    if os.path.commonpath([template_dir_real, original_real]) != template_dir_real:
        raise Http404('Original template file not found: %s' % override_obj.name)

    if not os.path.isfile(original_real):
        raise Http404('Original template file not found: %s' % override_obj.name)
    with open(original_real, encoding='utf-8', errors='replace') as original_file:
        original_lines = _normalize_lines_for_diff(original_file.read())

    context = {}
    context['name'] = override_obj.name
    context['version'] = override_obj.version
    context['diff'] = HtmlDiff().make_table(
            original_lines, override_lines,
            'original', f'override (id {template_id}, version {override_obj.version})')
    return render_to_response('utils/diff_templateoverride.html', request, context)
