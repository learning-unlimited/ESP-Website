from esp.program.models import Program
from esp.program.modules.base import ProgramModuleObj, needs_teacher, main_call, meets_deadline
from esp.web.util        import render_to_response
from esp.users.models   import ESPUser, UserBit
from esp.datatree.models import GetNode
from django import forms
from django.db.models.query import Q

#GetNode('V/Flags/Registration/Teacher/Acknowledgement')
#GetNode('V/Deadline/Registration/Teacher/Acknowledgement')

def teacheracknowledgementform_factory(prog):
    name = "TeacherAcknowledgementForm"
    bases = (forms.Form,)
    label = u"I have read the above, and commit to teaching my %s class on %s." % (prog.anchor.parent.friendly_name, prog.date_range())
    d = dict(acknowledgement=forms.BooleanField(required=True, label=label))
    return type(name, bases, d)

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
            context['form'] = teacheracknowledgementform_factory(prog)(request.POST)
            ub, created = UserBit.objects.get_or_create(user=self.user, qsc=self.program.anchor, verb=self.flags_verb)
            if context['form'].is_valid():
                ub.renew()
                return self.goToCore(tl)
            else:
                ub.expire()
        elif self.isCompleted():
            context['form'] = teacheracknowledgementform_factory(prog)({'acknowledgement': True})
        else:
            context['form'] = teacheracknowledgementform_factory(prog)()
        return render_to_response(self.baseDir()+'acknowledgement.html', request, (prog, tl), context)
    
    def teachers(self, QObject = False):
        """ Returns a list of teachers who have submitted the acknowledgement. """
        from datetime import datetime
        qf = Q(userbit__qsc=self.program_anchor_cached(), userbit__verb=GetNode('V/Flags/Registration/Teacher/Acknowledgement'), userbit__startdate__lte=datetime.now(), userbit__enddate__gte=datetime.now())
        if QObject is True:
            return {'acknowledgement': self.getQForUser(qf)}
        
        teacher_list = ESPUser.objects.filter(qf).distinct()
        
        return {'acknowledgement': teacher_list }#[t['user'] for t in teacher_list]}

    def teacherDesc(self):
        return {'acknowledgement': """Teachers who have submitted the acknowledgement for the program."""}    
    
    class Meta:
        abstract = True
    


