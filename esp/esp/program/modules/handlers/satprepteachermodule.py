
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, main_call, aux_call
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from esp.program.modules.forms.satprep import SATPrepTeacherInfoForm
from django import forms
from esp.program.models import Program
from esp.users.models   import ESPUser, User
from django.db.models.query import Q
from django.db        import models




class SATPrepTeacherModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "SATPrep Teacher Information",
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
        subject_list = module_ext.SATPrepTeacherModuleInfo.subjects()
        
	moduleinfos = module_ext.SATPrepTeacherModuleInfo.objects.filter(user = self.user,
		program = self.program)

	if request.method == 'POST':
	    if len(moduleinfos) == 0:
		form = SATPrepTeacherInfoForm(subject_list, request.POST)
		if form.is_valid():
		    info = form.save(commit = False)
		    info.user = self.user
		    info.program = self.program
		    info.save()
		    return self.goToCore(tl)
	    else:
		form = SATPrepTeacherInfoForm(subject_list, request.POST, instance = moduleinfos[0])
		if form.is_valid():
		    form.save()
		    return self.goToCore(tl)
	else:
	    if len(moduleinfos) == 0:
		form = SATPrepTeacherInfoForm(subject_list)
	    else:
		form = SATPrepTeacherInfoForm(subject_list, instance = moduleinfos[0])

	return render_to_response(self.baseDir()+'satprep_info.html', request, (prog, tl), {'form':form})
