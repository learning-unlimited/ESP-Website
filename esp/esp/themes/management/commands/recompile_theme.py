
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2014 by the individual contributors
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

import logging
logger = logging.getLogger(__name__)

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    """Recompile the current theme."""
    def handle(self, *args, **options):
        from esp.themes.controllers import ThemeController
        tc = ThemeController()
        # Resolve once before any attempt. recompile_theme() calls clear_theme()
        # which unsets current_theme_name, so a bare retry would fall back to
        # 'default' and fail with a misleading missing-pipeline error.
        theme_name = tc.get_current_theme()
        customization_name = tc.get_current_customization()
        try:
            # If this changes, make sure it still respects settings.LOCAL_THEME
            tc.recompile_theme(theme_name=theme_name,
                               customization_name=customization_name)
        except Exception:
            # Keep the first failure's traceback so the real root cause is
            # visible even when the retry fails for a different reason.
            logger.warning(
                "recompile_theme failed the first time for theme=%r "
                "customization=%r. Trying again...",
                theme_name,
                customization_name,
                exc_info=True,
            )
            tc.recompile_theme(theme_name=theme_name,
                               customization_name=customization_name)
