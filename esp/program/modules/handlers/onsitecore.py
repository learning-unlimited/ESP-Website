from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, needs_onsite
from esp.program.modules import module_ext
from esp.web.data        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.users.models    import ESPUser, UserBit, User
from esp.datatree.models import GetNode
from django              import forms
from django.http import HttpResponseRedirect
from esp.program.models import SATPrepRegInfo
from esp.program.modules.manipulators import OnSiteRegManipulator



class OnsiteCore(ProgramModuleObj):

    def createBit(self, extension):
        verb = GetNode('V/Registration/'+extension)
        ub = UserBit.objects.filter(user = self.student,
                                    verb = verb,
                                    qsc  = self.program.anchor)
        if len(ub) > 0:
            return False

        ub = UserBit()
        ub.verb = verb
        ub.qsc  = self.program.anchor
        ub.user = self.student
        ub.recursive = False
        ub.save()
        return True

    def deleteBit(self, extension):
        verb = GetNode('V/Registration/'+extension)
        ub = UserBit.objects.filter(user = self.student,
                                    verb = verb,
                                    qsc  = self.program.anchor)
        for userbit in ub:
            userbit.delete()

        return True

    def hasPaid(self):
        verb = GetNode('V/Registration/Paid')
        return UserBit.UserHasPerms(self.student,
                                    self.program.anchor,
                                    verb)
    
    def hasMedical(self):
        verb = GetNode('V/Registration/MedicalFiled')
        return UserBit.UserHasPerms(self.student,
                                    self.program.anchor,
                                    verb)
    def hasLiability(self):
        verb = GetNode('V/Registration/LiabilityFiled')
        return UserBit.UserHasPerms(self.student,
                                    self.program.anchor,
                                    verb)

        

    @needs_onsite
    def checkin(self, request, tl, one, two, module, extra, prog):
        error = False
        users = None
        if extra is not None:
            try:
                userid = int(extra)
            except:
                error = True
                
            if not error:
                user = ESPUser(ESPUser.objects.get(id = userid))
                self.student = user

                if request.method == 'POST':
                
                    if request.POST.has_key('paid'):
                        self.createBit('Paid')
                    else:
                        self.deleteBit('Paid')

                    if request.POST.has_key('liability'):
                        self.createBit('LiabilityFiled')
                    else:
                        self.deleteBit('LiabilityFiled')

                    if request.POST.has_key('medical'):
                        self.createBit('MedicalFiled')
                    else:
                        self.deleteBit('MedicalFiled')

                    return HttpResponseRedirect('/onsite/'+self.program.getUrlBase()+'/main')
                

                return render_to_response(self.baseDir()+'checkin.html', request, (prog, tl), {'module': self})
            
        if request.GET.has_key('userid'):
            try:
                userid = int(request.GET['userid'])
            except:
                error = True

            if not error:
                users = [ESPUser(user) for user in ESPUser.getAllOfType('Student', False).filter(id = userid)]
                if len(users) == 0:
                    error = True
                    users = None
                    
        elif request.GET.has_key('lastname'):
            users = [ESPUser(user) for user in
                     ESPUser.getAllOfType('Student', False).filter(last_name__icontains = request.GET['lastname']) ]
            if len(users) == 0:
                error = True
                users = None
            
        
        if users is None or error is True:
            return render_to_response(self.baseDir()+'checkin_search.html', request, (prog, tl), {'error': error})
        if len(users) == 1:
            return HttpResponseRedirect('/onsite/'+ self.program.getUrlBase()+'/checkin/' + str(users[0].id))
        else:
            users.sort()
            return render_to_response(self.baseDir()+'checkin_select.html', request, (prog, tl), {'users': users})

    @needs_onsite
    def reg(self, request, tl, one, two, module, extra, prog):
        manipulator = OnSiteRegManipulator()
	new_data = {}
	if request.method == 'POST':
            new_data = request.POST.copy()
            
            errors = manipulator.get_validation_errors(new_data)
            
            if not errors:
                manipulator.do_html2python(new_data)
                username = base_uname = (new_data['first_name'][0]+ \
                                         new_data['last_name']).lower()
                if ESPUser.objects.filter(username = username).count() > 0:
                    i = 2
                    username = base_uname + str(i)
                    while ESPUser.objects.filter(username = username).count() > 0:
                        i += 1
                        username = base_uname + str(i)
                new_user = User(username = username,
                                first_name = new_data['first_name'],
                                last_name  = new_data['last_name'],
                                email      = new_data['email'],
                                is_staff   = False,
                                is_superuser = False)
                new_user.save()

                self.student = new_user
                self.setCodeAndSendEmail(new_user)

                #update satprep information
                satprep = SATPrepRegInfo.getLastForProgram(new_user, self.program)
                satprep.old_math_score = new_data['old_math_score']
                satprep.old_verb_score = new_data['old_verb_score']
                satprep.old_writ_score = new_data['old_writ_score']
                satprep.save()

                if new_data['paid']:
                    self.createBit('Paid')
                else:
                    self.deleteBit('Paid')

                if new_data['medical']:
                    self.createBit('MedicalFiled')
                else:
                    self.deleteBit('MedicalFiled')

                if new_data['liability']:
                    self.createBit('LiabilityFiled')
                else:
                    self.deleteBit('LiabilityFiled')

                self.createBit('OnSite')

		v = GetNode( 'V/Flags/UserRole/Student')
		ub = UserBit()
		ub.user = new_user
		ub.recursive = False
		ub.qsc = GetNode('Q')
		ub.verb = v
		ub.save()
                
                new_user = ESPUser(new_user)

                
                return render_to_response(self.baseDir()+'reg_success.html', request, (prog, tl), {'user': new_user})
        
        else:
            new_data = {}
            errors = {}

	form = forms.FormWrapper(manipulator, new_data, errors)
	return render_to_response(self.baseDir()+'reg_info.html', request, (prog, tl), {'form':form})
        
    @needs_onsite
    def main(self, request, tl, one, two, module, extra, prog):
        """ Display a teacher eg page """
        context = {}
        modules = self.program.getModules(self.user, 'onsite')
        
        for module in modules:
            context = module.prepare(context)

                    
        context['modules'] = modules
        context['one'] = one
        context['two'] = two

        return render_to_response(self.baseDir()+'mainpage.html', request, (prog, tl), context)

    def isStep(self):
        return False
    
 

    def setCodeAndSendEmail(self, user):
        import string
        import random
        from esp.miniblog.models import Entry
        symbols = string.ascii_uppercase + string.digits 
        code = "".join([random.choice(symbols) for x in range(30)])
        msganchor = GetNode('Q/PasswordRecovery/'+str(user.id))

			
        ub = UserBit(user = user, qsc = msganchor, verb = GetNode('V/Subscribe'))
        ub.save()

        user.password = code
        user.save()

        Entry.post(None, msganchor,
                   '[ESP] A new account for '+self.program.niceName(),
                   """Hello,
 A new account was created in your name for esp.mit.edu at on-site registration.
 To access this account, please reset your password, available here:

 http://esp.mit.edu/myesp/recoveremail/?code="""+code+"""

 For reference, your username is: """+user.username+"""
 
 This will allow better communication and participation between you and the program.

 Thank you,
 MIT Educational Studies Program
 esp.mit.edu""", True)
        
