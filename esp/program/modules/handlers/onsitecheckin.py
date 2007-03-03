from esp.program.modules.base import ProgramModuleObj, needs_teacher, needs_student, needs_admin, usercheck_usetl, needs_onsite
from esp.program.modules import module_ext
from esp.web.util        import render_to_response
from django.contrib.auth.decorators import login_required
from esp.users.models    import ESPUser, UserBit, User
from esp.datatree.models import GetNode
from django              import forms
from django.http import HttpResponseRedirect
from esp.program.models import SATPrepRegInfo
from esp.users.views    import search_for_user
from esp.program.modules.manipulators import OnSiteRegManipulator
from esp.money.models   import Transaction


class OnSiteCheckinModule(ProgramModuleObj):

    def updatePaid(self, paid=True):
        t = Transaction.objects.filter(fbo    = self.student,
                                       anchor = self.program.anchor)
        if t.count() > 0 and not paid:
            for trans in t:
                trans.delete()

        if t.count() == 0 and paid:
            trans = Transaction(anchor = self.program.anchor,
                                fbo    = self.student,
                                payer  = self.student,
                                amount = 30.00,
                                line_item = 'Onsite payment for %s' % self.program.niceName(),
                                executed = True,
                                payment_type_id = 6
                                )
            trans.save()
            

    def createBit(self, extension):
        if key == 'Paid':
            self.updatePaid(True)
        verb = GetNode('V/Flags/Registration/'+extension)
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
        if key == 'Paid':
            self.updatePaid(False)
        verb = GetNode('V/Flags/Registration/'+extension)
        ub = UserBit.objects.filter(user = self.student,
                                    verb = verb,
                                    qsc  = self.program.anchor)
        for userbit in ub:
            userbit.delete()

        return True

    def hasAttended(self):
        verb = GetNode('V/Flags/Registration/Attended')
        return UserBit.UserHasPerms(self.student,
                                    self.program.anchor,
                                    verb)

    def hasPaid(self):
        verb = GetNode('V/Flags/Registration/Paid')
        return UserBit.UserHasPerms(self.student,
                                    self.program.anchor,
                                    verb) or \
               Transaction.objects.filter(fbo = self.student,
                                          anchor = self.program.anchor).count() > 0
    
    def hasMedical(self):
        verb = GetNode('V/Flags/Registration/MedicalFiled')
        return UserBit.UserHasPerms(self.student,
                                    self.program.anchor,
                                    verb)
    def hasLiability(self):
        verb = GetNode('V/Flags/Registration/LiabilityFiled')
        return UserBit.UserHasPerms(self.student,
                                    self.program.anchor,
                                    verb)

        

    @needs_onsite
    def checkin(self, request, tl, one, two, module, extra, prog):

        user, found = search_for_user(request, self.program.students_union())
        if not found:
            return user
        
        self.student = user
            
        if request.method == 'POST':
            for key in ['Attended','Paid','LiabilityFiled','MedicalFiled']:
                if request.POST.has_key(key):
                    self.createBit(key)
                else:
                    self.deleteBit(key)
                

            return self.goToCore(tl)

        return render_to_response(self.baseDir()+'checkin.html', request, (prog, tl), {'module': self})
