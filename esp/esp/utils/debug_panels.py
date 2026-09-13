
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2012 by the individual contributors
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

from debug_toolbar.panels.templates import TemplatesPanel as BaseTemplatesPanel
from django.core import signing

# Override the debug toolbar's TemplatesPanel to fix how it behaves with template overrides
class TemplatesPanel(BaseTemplatesPanel):
    def generate_stats(self, request, response):
        # Delegate the heavy lifting (context processing, template_dirs,
        # record_stats) to the parent. We only need to override behavior
        # for templates marked with our custom "(template override)" origin
        # marker: the parent would sign template.origin.name, but for these
        # we sign template.origin.template_name so the template-source view
        # can locate the underlying file.
        result = super().generate_stats(request, response)
        for template_data in self.templates:
            template = template_data.get("template")
            if (
                hasattr(template, "origin")
                and template.origin
                and template.origin.name == "(template override)"
            ):
                template.origin_hash = signing.dumps(template.origin.template_name)
        return result

import os
import threading
from django.utils.safestring import mark_safe
from debug_toolbar.panels.cache import CachePanel

_cache_panel_depth = threading.local()

def format_stacktrace_simple(trace):
    """Format stacktrace without using Django templates."""
    lines = []
    for frame in trace:
        filepath = frame[0]
        lineno = frame[1]
        func = frame[2]
        code = frame[3]

        # Split into directory and filename
        directory, filename = os.path.split(filepath)
        if directory:
            directory += os.sep

        lines.append(
            f'<span class="djdt-path">{directory}</span>'
            f'<span class="djdt-file">{filename}</span> in '
            f'<span class="djdt-func">{func}</span>'
            f'(<span class="djdt-lineno">{lineno}</span>)\n'
            f'  <span class="djdt-code">{code}</span>'
        )
    return mark_safe('\n'.join(lines))

# Override the debug toolbar's CachePanel to fix how it behaves with argcache
class SafeCachePanel(CachePanel):
    """Cache panel that prevents recursion when cache calls trigger template loading."""

    def _store_call_info(self, name, time_taken, return_value, args, kwargs, trace, template_info, backend):
        depth = getattr(_cache_panel_depth, 'depth', 0)
        _cache_panel_depth.depth = depth + 1

        try:
            if depth > 0:
                self.calls.append({
                    "name": name,
                    "time": time_taken,
                    "template_info": template_info,
                    "return_value": return_value,
                    "args": args,
                    "kwargs": kwargs,
                    "trace": format_stacktrace_simple(trace),
                    "backend": backend,
                })
            else:
                super()._store_call_info(
                    name, time_taken, return_value,
                    args, kwargs, trace, template_info, backend
                )
        finally:
            _cache_panel_depth.depth = depth
