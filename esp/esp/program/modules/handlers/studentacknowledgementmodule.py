from esp.program.models import Program
from esp.program.modules.base import ProgramModuleObj, needs_student, main_call, meets_deadline
from esp.utils.web import render_to_response
from esp.users.models   import ESPUser, Record
from django import forms
from django.db.models.query import Q
from esp.middleware.threadlocalrequest import get_current_request

def studentacknowledgementform_factory(prog):
    name = "StudentAcknowledgementForm"
    bases = (forms.Form,)

    label = u"By checking this box, I acknowledge that I have read and understood the above contract, and agree to abide by it. I understand that should I break this contract, I may be asked to leave the program."

    d = dict(acknowledgement=forms.BooleanField(required=True, label=label))
    return type(name, bases, d)

class StudentAcknowledgementModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Student Acknowledgement",
            "link_title": "Student Acknowledgement",
            "module_type": "learn",
            "required": True,
            "choosable": 0,
        }

    def isCompleted(self):
        return Record.objects.filter(user=get_current_request().user,
                                     program=self.program,
                                     event="studentacknowledgement").exists()

    @main_call
    @needs_student
    @meets_deadline('/Acknowledgement')
    def acknowledgement(self, request, tl, one, two, module, extra, prog):
        context = {'prog': prog}
        if request.method == 'POST':
            context['form'] = studentacknowledgementform_factory(prog)(request.POST)
            rec, created = Record.objects.get_or_create(user=request.user,
                                                        program=self.program,
                                                        event="studentacknowledgement")
            if context['form'].is_valid():
                return self.goToCore(tl)
            else:
                rec.delete()
        elif self.isCompleted():
            context['form'] = studentacknowledgementform_factory(prog)({'acknowledgement': True})
        else:
            context['form'] = studentacknowledgementform_factory(prog)()
        return render_to_response(self.baseDir()+'acknowledgement.html', request, context)

    def students(self, QObject = False):
        """ Returns a list of students who have submitted the acknowledgement. """
        qo = Q(record__program=self.program, record__event="studentacknowledgement")
        if QObject is True:
            return {'acknowledgement': qo}

        student_list = ESPUser.objects.filter(qo).distinct()

        return {'acknowledgement': student_list }

    def studentDesc(self):
        return {'acknowledgement': """Students who have submitted the acknowledgement for the program"""}

    class Meta:
        proxy = True
        app_label = 'modules'
