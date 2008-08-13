
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, main_call, aux_call
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from esp.program.manipulators import SATPrepTeacherInfoManipulator
from django import oldforms
from esp.program.models import Program
from esp.users.models   import ESPUser, User
from esp.db.models import Q
from django.db        import models




class SATPrepTeacherModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "link_title": "SATPrep Information",
            "module_type": "teach",
            "seq": 50
            }

    def teachers(self,QObject = False):
        if QObject:
            return {'teachers_satprepinfo': self.getQForUser(Q(satprepteachermoduleinfo__program = self.program))}
                    
        teachers = User.objects.filter(satprepteachermoduleinfo__program = self.program).distinct()
        return {'teachers_satprepinfo': teachers }

    def teacherDesc(self):
        return {'teachers_satprepinfo': """Teachers who have entered SATPrep-specific information."""}

    def isCompleted(self):
        return module_ext.SATPrepTeacherModuleInfo.objects.filter(user = self.user,
                                                       program = self.program).count() > 0


    @main_call
    @needs_teacher
    def satprepinfo(self, request, tl, one, two, module, extra, prog):
        manipulator = SATPrepTeacherInfoManipulator(module_ext.SATPrepTeacherModuleInfo.subjects())
        
	new_data = {}
	if request.method == 'POST':
		new_data = request.POST.copy()
		
		errors = manipulator.get_validation_errors(new_data)
		
		if not errors:
                    manipulator.do_html2python(new_data)
                    moduleinfos = module_ext.SATPrepTeacherModuleInfo.objects.filter(user = self.user,
                                                                                     program = self.program)
                    if len(moduleinfos) == 0:
                        new_reginfo = module_ext.SATPrepTeacherModuleInfo()
                        new_reginfo.user = self.user
                        new_reginfo.program = self.program
                    else:
                        new_reginfo = moduleinfos[0]

                    for k in new_data.keys():
                        new_reginfo.__dict__[k] = new_data[k]

                    new_reginfo.save()
                
                    return self.goToCore(tl)
	else:
                moduleinfos = module_ext.SATPrepTeacherModuleInfo.objects.filter(user = self.user,
                                                                                 program = self.program)
                if len(moduleinfos) == 0:
                    new_data = {}
                else:
                    new_data = moduleinfos[0].__dict__
		
		errors = {}

	form = oldforms.FormWrapper(manipulator, new_data, errors)
	return render_to_response(self.baseDir()+'satprep_info.html', request, (prog, tl), {'form':form})


