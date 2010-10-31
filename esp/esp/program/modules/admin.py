
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
  Email: web-team@lists.learningu.org
"""

from django.contrib import admin
from esp.program.modules.module_ext import DBReceipt, StudentClassRegModuleInfo, ClassRegModuleInfo, SATPrepTeacherModuleInfo, SATPrepAdminModuleInfo
from esp.program.modules.module_ext import RemoteProfile
from esp.program.modules.base import ProgramModuleObj

admin.site.register(DBReceipt)

admin.site.register(SATPrepAdminModuleInfo)

class SCRMIAdmin(admin.ModelAdmin):
    pass
admin.site.register(StudentClassRegModuleInfo, SCRMIAdmin)

class CRMIAdmin(admin.ModelAdmin):
    pass
admin.site.register(ClassRegModuleInfo, CRMIAdmin)

class ProgramModelObjAdmin(admin.ModelAdmin):
    list_display = ('program', 'module')
    pass
admin.site.register(ProgramModuleObj, ProgramModelObjAdmin)

admin.site.register(SATPrepTeacherModuleInfo)

class RemoteProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'program', 'volunteer', 'need_bus')
admin.site.register(RemoteProfile, RemoteProfileAdmin)
