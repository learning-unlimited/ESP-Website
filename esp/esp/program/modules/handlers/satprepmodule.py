
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, main_call, aux_call, meets_deadline
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from esp.program.modules.forms.satprep import SATPrepInfoForm
from esp.program.models import SATPrepRegInfo
from esp.users.models   import ESPUser
from django.contrib.auth.models import User
from django.db.models.query     import Q
from esp.middleware.threadlocalrequest import get_current_request


class SATPrepModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "SATPrep Information",
            "link_title": "Program-specific Information",
            "module_type": "learn",
            "seq": 10,
            "required": True
            }

    def get_msg_vars(self, user, key):
        user = ESPUser(user)
        if key == 'diag_sat_scores' or key == 'old_sat_scores' or key == 'prac_sat_scores':
            test_type = key.split('_')[0]
            
            if user.isStudent():
                foo = SATPrepRegInfo.getLastForProgram(user, self.program)
                
                scores = 'Your %s SAT scores:\n' % {'prac': 'practice',
                                                    'diag': 'diagnostic',
                                                    'old':  'original'}[test_type]
                for test in ['Math','Verbal','Writing']:
                    curscore = foo.__dict__['%s_%s_score' % (test_type, test[0:4].lower())]
                    if curscore is None or curscore < 200 or curscore > 800:
                        scores += '%s: Not Available\n' % test
                    else:
                        scores += '%s: %s\n' % (test, curscore)
                return scores

        return ''
    
    def students(self,QObject = False):
        if QObject:
            return {'satprepinfo': self.getQForUser(Q(satprepreginfo__program = self.program)),
                    'satprep_diag_current': self.getQForUser(Q(satprepreginfo__program = self.program) & 
                                                             (Q(satprepreginfo__diag_math_score__isnull=False) |
                                                              Q(satprepreginfo__diag_verb_score__isnull=False) |
                                                              Q(satprepreginfo__diag_writ_score__isnull=False))),
                    'satprep_mathdiag': self.getQForUser(Q(satprepreginfo__diag_math_score__isnull = False)),
                    'satprep_mathprac': self.getQForUser(Q(satprepreginfo__prac_math_score__isnull = False)),
                    'satprep_mathold' : self.getQForUser(Q(satprepreginfo__old_math_score__isnull = False)),
                    'satprep_writdiag': self.getQForUser(Q(satprepreginfo__diag_writ_score__isnull = False)),
                    'satprep_writold': self.getQForUser(Q(satprepreginfo__old_writ_score__isnull = False)),
                    'satprep_verbdiag': self.getQForUser(Q(satprepreginfo__diag_verb_score__isnull = False)),
                    'satprep_verbold': self.getQForUser(Q(satprepreginfo__old_verb_score__isnull = False)),
                    'satprep_writprac': self.getQForUser(Q(satprepreginfo__prac_writ_score__isnull = False)),
                    'satprep_verbprac': self.getQForUser(Q(satprepreginfo__prac_verb_score__isnull = False)),
                    }
        
        studentswritold = ESPUser.objects.filter(Q(satprepreginfo__old_writ_score__isnull = False)).distinct()
        studentsmathold = ESPUser.objects.filter(Q(satprepreginfo__old_math_score__isnull = False)).distinct()
        studentsverbold = ESPUser.objects.filter(Q(satprepreginfo__old_verb_score__isnull = False)).distinct()
        
        studentswritdiag = ESPUser.objects.filter(Q(satprepreginfo__diag_writ_score__isnull = False)).distinct()
        studentsmathdiag = ESPUser.objects.filter(Q(satprepreginfo__diag_math_score__isnull = False)).distinct()
        studentsverbdiag = ESPUser.objects.filter(Q(satprepreginfo__diag_verb_score__isnull = False)).distinct()

        studentswritprac = ESPUser.objects.filter(Q(satprepreginfo__prac_writ_score__isnull = False)).distinct()
        studentsmathprac = ESPUser.objects.filter(Q(satprepreginfo__prac_math_score__isnull = False)).distinct()
        studentsverbprac = ESPUser.objects.filter(Q(satprepreginfo__prac_verb_score__isnull = False)).distinct()

        students = ESPUser.objects.filter(satprepreginfo__program = self.program).distinct()
        students_diag_current = ESPUser.objects.filter(Q(satprepreginfo__program = self.program) & 
                                                             (Q(satprepreginfo__diag_math_score__isnull=False) |
                                                              Q(satprepreginfo__diag_verb_score__isnull=False) |
                                                              Q(satprepreginfo__diag_writ_score__isnull=False)))

        return {'satprepinfo': students,
                'satprep_diag_current': students_diag_current,
                'satprep_mathold': studentsmathold,
                'satprep_verbold': studentsverbold,
                'satprep_writold': studentswritold,
                'satprep_mathdiag': studentsmathdiag,
                'satprep_verbdiag': studentsverbdiag,
                'satprep_writdiag': studentswritdiag,
                'satprep_mathprac': studentsmathprac,
                'satprep_verbprac': studentsverbprac,
                'satprep_writprac': studentswritprac,
                }
    

    def studentDesc(self):
        return {'satprepinfo': """Students who have filled out the SAT Prep information.""",
                'satprep_diag_current': """Students who have current diagnostic exam scores.""",
                'satprep_mathdiag': """Students who have an SAT math diagnostic score.""",
                'satprep_writdiag': """Students who have an SAT writing diagnostic score.""",
                'satprep_verbdiag': """Students who have an SAT verbal diagnostic score.""",
                'satprep_mathold': """Students who have an old SAT math score.""",
                'satprep_writold': """Students who have an old SAT writing score.""",
                'satprep_verbold': """Students who have an old SAT verbal score.""",
                'satprep_mathprac': """Students who have a practice SAT math score.""",
                'satprep_verbprac': """Students who have a practice SAT verbal score.""",
                'satprep_writprac': """Students who have a practice SAT writing score.""",
                }
    
    def isCompleted(self):
        
	satPrep = SATPrepRegInfo.getLastForProgram(get_current_request().user, self.program)
	return satPrep.id is not None

    @main_call
    @needs_student
    @meets_deadline()
    def satprepinfo(self, request, tl, one, two, module, extra, prog):
	if request.method == 'POST':
            form = SATPrepInfoForm(request.POST)

            if form.is_valid():
                reginfo = SATPrepRegInfo.getLastForProgram(request.user, prog)
                form.instance = reginfo
                form.save()

                return self.goToCore(tl)
	else:
            satPrep = SATPrepRegInfo.getLastForProgram(request.user, prog)
            form = SATPrepInfoForm(instance = satPrep)

	return render_to_response('program/modules/satprep_stureg.html', request, (prog, tl), {'form':form})



    class Meta:
        abstract = True

