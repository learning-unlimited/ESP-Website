
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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl
from esp.web.views.myesp import profile_editor
from esp.program.models import RegistrationProfile
from esp.users.models   import ESPUser, User
from django.db.models.query import Q
from esp.middleware.threadlocalrequest import get_current_request

class EmailVerifyModule(ProgramModuleObj):
    """ This module will allow users to verify that their email accounts work. """
    def students(self, QObject = False):
        Q_students =  Q(registrationprofile__email_verified = True) & \
                      Q(groups__name="Student")
        if QObject:
            return {'student_emailverified': Q_students}

        students = ESPUser.objects.filter(Q_students).distinct()
        return {'student_emailverified': students }

    def studentDesc(self):
        return {'student_emailverified': """Students who have verified their email address."""}


    def teachers(self, QObject = False):
        Q_teachers =  Q(registrationprofile__email_verified = True) & \
                      Q(groups__name="Teacher")
        if QObject:
            return {'teacher_emailverified': Q_teachers}
                                 

        teachers = ESPUser.objects.filter(Q_teachers).distinct()
        return {'teacher_emailverified': teachers }


    def teacherDesc(self):
        return {'teacher_emailverified': """Teachers who have verified their email address."""}

    def get_msg_vars(self, user, key):
        user = ESPUser(user)
        if key == 'verifyemaillink':
            
            return 'http://esp.mit.edu/%s/%s/verify_email_code?code=%s' % \
                   ('teach', self.program.getUrlBase(), \
                    RegistrationProfile.getLastForProfile(user, self.program).emailverifycode)

        return ''



    def verify_email(self):
        import string
        import random
        from esp.users.models import PersistentQueryFilter
        from esp.dbmail.models import MessageRequest
        from django.template import loader
        
        
        symbols = string.ascii_uppercase + string.digits
        code = "".join([random.choice(symbols) for x in range(30)])

        regProf = RegistrationProfile.getLastForProgram(get_current_request().user, self.program)

        if regProf.email_verified:
            return self.goToCore(tl)

        if request.method == 'POST' and request.POST.has_key('verify_me'):
            # create the variable modules
            variable_modules = {'program': self.program, 'user': get_current_request().user}
            
            # get the filter object
            filterobj = PersistentQueryFilter.getFilterFromQ(Q(id = get_current_request().user.id),
                                                             User,
                                                             'User %s' % get_current_request().user.username)

            newmsg_request = MessageRequest.createRequest(var_dict   = variable_modules,
                                                          subject    = '[ESP] Email Verification For esp.mit.edu',
                                                          recipients = filterobj,
                                                          sender     = '"MIT Educational Studies Program" <esp@mit.edu>',
                                                          creator    = self,
                                                          msgtext    = loader.find_template_source('email/verify')[0])
            
            newmsg_request.save()
            
            return render_to_response(self.baseDir() + 'emailsent.html', request, {})

        return render_to_response(self.baseDir() + 'sendemail.html', request, {})
    



    class Meta:
        abstract = True

