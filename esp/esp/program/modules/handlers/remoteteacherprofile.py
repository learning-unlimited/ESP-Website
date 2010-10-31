
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
from esp.program.modules.base    import ProgramModuleObj, needs_teacher, meets_deadline, main_call, aux_call
from esp.program.modules         import module_ext
from esp.program.modules.forms.profile import RemoteTeacherProfileForm
from esp.datatree.models import *
from esp.web.util                import render_to_response
from django.core.mail            import send_mail
from django.db.models.query      import Q
from esp.users.models            import ESPUser, User

class RemoteTeacherProfile(ProgramModuleObj):
    """ This program module allows teachers to select how they are going to do things with respect to having a program far away. (i.e. do they need transportation, when do they need transportation, etc.)"""
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Remote-Teacher Profile Editor",
            "link_title": "Edit your Program-Specific Teacher Information",
            "module_type": "teach",
            "seq": 10
            }

    def getTimes(self):
        times = self.program.getTimeSlots()
        return [(str(x.id),x.short_description) for x in times]

    def teachers(self, QObject = False):
        Q_teachers = Q(remoteprofile__program = self.program)
        if QObject:
            return {'teacher_remoteprofile': self.getQForUser(Q_teachers)}
        
        teachers = User.objects.filter(Q_teachers).distinct()
        return {'teacher_remoteprofile': teachers}

    def teacherDesc(self):
        return {'teacher_remoteprofile': """Teachers who have completed the remote volunteer profile."""}

    def isCompleted(self):
        regProf, created = module_ext.RemoteProfile.objects.get_or_create(user = self.user, program = self.program)
        return not created

    @main_call
    @meets_deadline()
    @needs_teacher
    def editremoteprofile(self, request, tl, one, two, module, extra, prog):
 
        context = {'module': self}
        
        profile, created  = module_ext.RemoteProfile.objects.get_or_create(user = self.user, program = self.program)
        if created:
            profile.save()
        if request.method == 'POST':
            form = RemoteTeacherProfileForm(self, request.POST)

            if form.is_valid():
                form.instance = profile
                form.save()
                
                return self.goToCore(tl)
                            
        else:
            form = RemoteTeacherProfileForm(module = self, instance = profile)
        context['form'] = form

        return render_to_response(self.baseDir() + 'editprofile.html', request, (prog, tl), context)


