from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl
from esp.web.views.myesp import profile_editor
from esp.program.models import RegistrationProfile
from esp.users.models   import ESPUser
from esp.db.models import Q


class EmailVerifyModule(ProgramModuleObj):
    """ This module will allow users to verify that their email accounts work. """
    def students(self, QObject = False):
        Q_students =  Q(registrationprofile__email_verified = True) & \
                                             Q(userbit__qsc  = GetNode('Q')) &\
                                             Q(userbit__verb = GetNode('V/Flags/UserRole/Student'))
        if QObject:
            return {'student_emailverified': Q_students}
                                 

        students = ESPUser.objects.filter(Q_students).distinct()
        return {'student_emailverified': students }

    def studentDesc(self):
        return {'student_emailverified': """Students who have verified their email address."""}


    def teachers(self, QObject = False):
        Q_teachers =  Q(registrationprofile__email_verified = True) & \
                                             Q(userbit__qsc  = GetNode('Q')) &\
                                             Q(userbit__verb = GetNode('V/Flags/UserRole/Teacher'))
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
        from django.template import loader, Context
        
        
        symbols = string.ascii_uppercase + string.digits
        code = "".join([random.choice(symbols) for x in range(30)])

        regProf = RegistrationProfile.getLastForProgram(self.user, self.program)

        if regProf.email_verified:
            return self.goToCore(tl)

        if request.method == 'POST' and request.POST.has_key('verify_me'):
            # create the variable modules
            variable_modules = {'program': self.program, 'user': self.user}
            
            # get the filter object
            filterobj = PersistentQueryFilter.getFilterFromQ(Q(id = self.user.id),
                                                             User,
                                                             'User %s' % self.username)

            newmsg_request = MessageRequest.createRequest(var_dict   = variable_modules,
                                                          subject    = '[ESP] Email Verification For esp.mit.edu',
                                                          recipients = filterobj,
                                                          sender     = '"MIT Educational Studies Program" <esp@mit.edu>',
                                                          creator    = self,
                                                          msgtext    = loader.find_template_source('email/verify')[0])
            
            newmsg_request.save()
            
            return render_to_response(self.baseDir() + 'emailsent.html', request, (prog, tl), {})

        return render_to_response(self.baseDir() + 'sendemail.html', request, (prog, tl), {})
    

