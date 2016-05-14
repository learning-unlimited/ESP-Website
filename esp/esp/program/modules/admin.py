
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
from esp.admin import admin_site
from esp.program.modules.module_ext import DBReceipt, StudentClassRegModuleInfo, ClassRegModuleInfo
from esp.program.modules.base import ProgramModuleObj

class Admin_DBReceipt(admin.ModelAdmin):
    list_display = (
        'action',
        'program',
    )
    list_filter = ('action', 'program')
admin_site.register(DBReceipt, Admin_DBReceipt)

class SCRMIAdmin(admin.ModelAdmin):
    list_display = ('program',)
    list_filter = ('program',)
    search_fields = ('program__name',)
admin_site.register(StudentClassRegModuleInfo, SCRMIAdmin)

class CRMIAdmin(admin.ModelAdmin):
    list_display = ('program',)
    list_filter = ('program',)
    search_fields = ('program__name',)
admin_site.register(ClassRegModuleInfo, CRMIAdmin)

class ProgramModelObjAdmin(admin.ModelAdmin):
    list_display = (
        'program',
        'module',
        'seq',
        'required',
        'required_label',
    )
    list_filter = ('program', 'module')
    search_fields = ('program__name', 'program__url', 'module__admin_title', 'module__link_title')
admin_site.register(ProgramModuleObj, ProgramModelObjAdmin)
