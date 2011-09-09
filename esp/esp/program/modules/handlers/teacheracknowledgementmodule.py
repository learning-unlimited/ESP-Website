from esp.program.models import Program
from esp.program.modules.base import ProgramModuleObj, needs_teacher, main_call, meets_deadline
from esp.web.util        import render_to_response
from esp.users.models   import ESPUser, UserBit
from esp.datatree.models import GetNode
from django import forms
from django.db.models.query import Q

GetNode('V/Flags/Registration/Teacher/Acknowledgement')
GetNode('V/Deadline/Registration/Teacher/Acknowledgement')

class TeacherAcknowledgementForm(forms.Form):
    label = u'''I have read and agree to the terms and conditions above.'''
    acknowledgement = forms.BooleanField(required=True, label=label)


class TeacherAcknowledgementModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Teacher Acknowledgement",
            "link_title": "Teacher Acknowledgement",
            "module_type": "teach",
            "main_call": "acknowledgement",
            "aux_calls": "",
            "required": False,
        }
    
    @property
    def flags_verb(self): 
        return GetNode('V/Flags/Registration/Teacher/Acknowledgement')
    
    @property
    def deadline_verb(self):
        return GetNode('V/Deadline/Registration/Teacher/Acknowledgement')
    
    def isCompleted(self):
        return bool(UserBit.objects.filter(Q(user=self.user, qsc=self.program.anchor, verb=self.flags_verb) & UserBit.not_expired()))
    
    @main_call
    @needs_teacher
    @meets_deadline('/Acknowledgement')
    def acknowledgement(self, request, tl, one, two, module, extra, prog):
        context = {'prog': prog}
        if request.method == 'POST':
            context['form'] = TeacherAcknowledgementForm(request.POST)
            ub, created = UserBit.objects.get_or_create(user=self.user, qsc=self.program.anchor, verb=self.flags_verb)
            if context['form'].is_valid():
                ub.renew()
                return self.goToCore(tl)
            else:
                ub.expire()
        elif self.isCompleted():
            context['form'] = TeacherAcknowledgementForm({'acknowledgement': True})
        else:
            context['form'] = TeacherAcknowledgementForm()
        return render_to_response(self.baseDir()+'acknowledgement.html', request, (prog, tl), context)



