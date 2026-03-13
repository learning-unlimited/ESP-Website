
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
from django.utils.translation import ugettext_lazy as _
from django.core import signing
from os.path import normpath

# Override the debug toolbar's TemplatesPanel to fix how it behaves with template overrides
class TemplatesPanel(BaseTemplatesPanel):
    def generate_stats(self, request, response):
        template_context = []
        for template_data in self.templates:
            info = {}
            # Clean up some info about templates
            template = template_data.get("template", None)
            if hasattr(template, "origin") and template.origin and template.origin.name:
                template.origin_name = template.origin.name
                if template.origin.name == "(template override)":
                    template.origin_hash = signing.dumps(template.origin.template_name)
                else:
                    template.origin_hash = signing.dumps(template.origin.name)
            else:
                template.origin_name = _("No origin")
                template.origin_hash = ""
            info["template"] = template
            # Clean up context for better readability
            if self.toolbar.config["SHOW_TEMPLATE_CONTEXT"]:
                context_list = template_data.get("context", [])
                info["context"] = "\n".join(context_list)
            template_context.append(info)

        # Fetch context_processors/template_dirs from any template
        if self.templates:
            context_processors = self.templates[0]["context_processors"]
            template = self.templates[0]["template"]
            # django templates have the 'engine' attribute, while jinja
            # templates use 'backend'
            engine_backend = getattr(template, "engine", None) or getattr(
                template, "backend"
            )
            template_dirs = engine_backend.dirs
        else:
            context_processors = None
            template_dirs = []

        self.record_stats(
            {
                "templates": template_context,
                "template_dirs": [normpath(x) for x in template_dirs],
                "context_processors": context_processors,
            }
        )

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

    def _store_call_info(self, sender, name, time_taken, return_value, args, kwargs, trace, template_info, backend, **kw):
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
                    sender, name, time_taken, return_value,
                    args, kwargs, trace, template_info, backend, **kw
                )
        finally:
            _cache_panel_depth.depth = depth
