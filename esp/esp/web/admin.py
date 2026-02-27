
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
from django.contrib import admin
from django.contrib import messages
from esp.admin import admin_site
from esp.web.models import NavBarEntry, NavBarCategory

class NavBarEntryAdmin(admin.ModelAdmin):
    list_display = ('category', 'sort_rank', 'text', 'link')
    list_filter = ('category',)

class NavBarCategoryAdmin(admin.ModelAdmin):
    def delete_model(self, request, obj):
        if obj.name == "default":
            self.message_user(
                request,
                'The "default" nav category cannot be deleted because it is required by the system.',
                level = messages.ERROR,
            )
        return super().delete_model(request, obj)
    def has_delete_permission(self, request, obj = None):
        if obj and obj.name == "default":
            return False
        return super().has_delete_permission(request, obj)

admin_site.register(NavBarEntry, NavBarEntryAdmin)
admin_site.register(NavBarCategory, NavBarCategoryAdmin)
