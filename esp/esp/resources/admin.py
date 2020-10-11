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
  Email: web-team@learningu.org
"""

from django.contrib import admin
from esp.admin import admin_site

from esp.resources.models import ResourceType, ResourceRequest, Resource, ResourceAssignment

class ResourceTypeAdmin(admin.ModelAdmin):
    def rt_choices(self, obj):
        return "%s" % str(obj.choices)
    rt_choices.short_description = 'Choices'

    list_display = ('name', 'description', 'only_one', 'consumable', 'autocreated', 'hidden', 'priority_default', 'rt_choices', 'program')
    search_fields = ['name', 'description', 'consumable', 'priority_default',
            'attributes_pickled', 'program__name']

class ResourceRequestAdmin(admin.ModelAdmin):
    list_display = ('target', 'res_type', 'desired_value')
    list_filter = ('res_type__program',)
    search_fields = ['target__parent_class__title', '=target__parent_class__id', 'res_type__name',
            'res_type__description', 'res_type__program__name',
            'desired_value']

class ResourceAdmin(admin.ModelAdmin):
    def program(obj):
        return obj.event.program.name
    list_display = ('name', 'res_type', 'num_students', 'event', 'res_group', program)
    list_filter = ('event__program',)
    search_fields = ('name', 'res_type__name', 'res_type__description',
            'res_type__attributes_pickled', 'event__program__name',
            'num_students', 'event__name', 'event__short_description',
            '=res_group__id')

class ResourceAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'resource', 'target', 'assignment_group', 'returned')
    search_fields = ('=id', 'resource__name', 'target__parent_class__title')

admin_site.register(ResourceType, ResourceTypeAdmin)
admin_site.register(ResourceRequest, ResourceRequestAdmin)
admin_site.register(Resource, ResourceAdmin)
admin_site.register(ResourceAssignment, ResourceAssignmentAdmin)
