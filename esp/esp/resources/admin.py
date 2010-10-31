__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2008 by the individual contributors
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
  Email: web-team@lists.learningu.org
"""

from django.contrib import admin

from esp.resources.models import ResourceType, ResourceRequest, Resource

class ResourceTypeAdmin(admin.ModelAdmin):
    def rt_choices(self, obj):
        return "%s" % str(obj.choices)
    rt_choices.short_description = 'Choices'

    list_display = ('name', 'description', 'consumable', 'priority_default', 'rt_choices', 'distancefunc', 'program')
    search_fields = ['name', 'description', 'consumable', 'priority_default', 'rt_choices', 'distancefunc', 'program']

class ResourceRequestAdmin(admin.ModelAdmin):
    list_display = ('target', 'res_type', 'desired_value')
    search_fields = ['target', 'res_type', 'desired_value']

admin.site.register(ResourceType, ResourceTypeAdmin)
admin.site.register(ResourceRequest, ResourceRequestAdmin)
admin.site.register(Resource)
