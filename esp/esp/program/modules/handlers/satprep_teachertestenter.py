
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.miniblog.models import Entry
from esp.datatree.models import GetNode
from esp.users.views import search_for_user
from esp.program.manipulators import SATPrepDiagManipulator
from django import forms
from esp.program.models import SATPrepRegInfo


class SATPrepTeacherInput(ProgramModuleObj):

    
    @needs_teacher
    def satprepuserdiagnostic(self, request, tl, one, two, module, extra, prog):
        context = {}
        response, userfound = search_for_user(request, self.program.students_union())
        if not userfound:
            return response
        user = response
        
        manipulator = SATPrepDiagManipulator()
        new_data = {}
        if request.method == 'POST':
                new_data = request.POST.copy()

                errors = manipulator.get_validation_errors(new_data)

                if not errors:
                        manipulator.do_html2python(new_data)
                        new_reginfo = SATPrepRegInfo.getLastForProgram(user, prog)
                        new_reginfo.addOrUpdate(new_data, user, prog)

                        return self.goToCore(tl)
        else:
                satPrep = SATPrepRegInfo.getLastForProgram(user, prog)

                new_data = satPrep.updateForm(new_data)
                errors = {}

        form = forms.FormWrapper(manipulator, new_data, errors)
        return render_to_response(self.baseDir()+'satprep_diag.html', request, (prog, tl), {'form':form,
                                                                                            'user':user})


        

        

    def isStep(self):
        return False
    

