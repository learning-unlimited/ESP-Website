
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
from esp.program.modules.base    import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, meets_deadline
from esp.program.modules         import module_ext, manipulators
from esp.program.models          import Program, Class, ClassCategories
from esp.datatree.models         import DataTree, GetNode
from esp.web.util                import render_to_response
from django                      import forms
from django.utils.datastructures import MultiValueDict
from esp.cal.models              import Event
from django.core.mail            import send_mail
from esp.miniblog.models         import Entry
from django.core.cache           import cache
from esp.db.models               import Q
from esp.users.models            import ESPUser

class RemoteTeacherProfile(ProgramModuleObj):
    """ This program module allows teachers to select how they are going to do things with respect to having a program far away. (i.e. do they need transportation, when do they need transportation, etc.)"""


    def getTimes(self):
        times = self.program.getTimeSlots()
        return [(str(x.id),x.friendly_name) for x in times]

    def teachers(self, QObject = False):
        Q_teachers = Q(remoteteacherparticipationprofile__program = self.program)
        if QObject:
            return {'teacher_remoteprofile': Q_teachers}

        teachers = ESPUser.objects.filter(Q_teachers).distinct()
        return {'teacher_remoteprofile': teachers }

    def teacherDesc(self):
        return {'teacher_remoteprofile': """Teachers who have completed the remote volunteer profile."""}

    def isCompleted(self):
        regProf, created = module_ext.RemoteProfile.objects.get_or_create(user = self.user,
                                                                                              program = self.program)
        
        return not created


 
    @meets_deadline()
    @needs_teacher
    def editremoteprofile(self, request, tl, one, two, module, extra, prog):
 
        new_data = request.POST.copy()
        context = {'module': self}
        
        manipulator = manipulators.RemoteTeacherManipulator(self)

        profile, created  = module_ext.RemoteProfile.objects.get_or_create(user = self.user, program = self.program)
        profile.save()
        

        if request.method == 'POST':
            #manipulator.prepare(new_data)
            
            errors = manipulator.get_validation_errors(new_data)
            if not errors:
                manipulator.do_html2python(new_data)

                for k, v in new_data.items():
                    if k != 'volunteer_times':
                        profile.__dict__[k] = v


                profile.volunteer_times.clear()


                for block in new_data.getlist('volunteer_times'):
                    try:
                        tmpQsc = DataTree.objects.get(id = int(block))
                        profile.volunteer_times.add(tmpQsc)
                    except:
                        raise ESPError(), "Invalid timeblock given."

                profile.save()

                
                return self.goToCore(tl)
                            
        else:
            errors = {}
            new_data.update(profile.__dict__)
            
            new_data['volunteer_times'] = [x.id for x in profile.volunteer_times.all()]
            new_data.setlist('volunteer_times', [x.id for x in profile.volunteer_times.all()])
            #assert False, new_data
        context['form'] = forms.FormWrapper(manipulator, new_data, errors)

        return render_to_response(self.baseDir() + 'editprofile.html', request, (prog, tl), context)


