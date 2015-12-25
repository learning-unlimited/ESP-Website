
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2011 by the individual contributors
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

""" This file merely imports all of the template tag functions that are cached.
    This populates the ArgCache registry with the appropriate info so that it's
    ready to use when the tags get loaded and used in a template.  Otherwise,
    you'll get cache initialization errors.
"""

from esp.miniblog.templatetags.render_blog import render_blog
from esp.miniblog.templatetags.render_blog import render_comments

from esp.program.templatetags.class_render import render_class
from esp.program.templatetags.class_render import render_class_core
from esp.program.templatetags.class_render import render_class_preview
from esp.program.templatetags.class_render import render_class_row

from esp.program.templatetags.class_render_row import render_class_copy_row
from esp.program.templatetags.class_render_row import render_class_teacher_list_row

from esp.qsd.templatetags.render_qsd import render_qsd
from esp.qsd.templatetags.render_qsd import render_inline_qsd

from esp.web.templatetags.navbar import navbar_gen

from esp.web.templatetags.topbar import get_primary_nav


