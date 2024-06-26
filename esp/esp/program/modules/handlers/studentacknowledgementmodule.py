from __future__ import absolute_import
from esp.program.modules.base import ProgramModuleObj, needs_student_in_grade, main_call, meets_deadline
from esp.utils.web import render_to_response
from esp.users.models   import ESPUser, Record, RecordType
from django import forms
from django.db.models.query import Q
from esp.middleware.threadlocalrequest import get_current_request
import six

def studentacknowledgementform_factory(prog):
    name = "StudentAcknowledgementForm"
    bases = (forms.Form,)

    label = six.u("By checking this box, I acknowledge that I have read and understood the above contract, and agree to abide by it. I understand that should I break this contract, I may be asked to leave the program.")

    d = dict(acknowledgement=forms.BooleanField(required=True, label=label))
    return type(name, bases, d)

class StudentAcknowledgementModule(ProgramModuleObj):
    doc = """Serves a form asking students to acknowledge some agreement."""

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
        if hasattr(self, 'user'):
            user = self.user
        else:
            user = get_current_request().user
        return Record.objects.filter(user=user,
                                     program=self.program,
                                     event__name="studentacknowledgement").exists()

    @main_call
    @needs_student_in_grade
    @meets_deadline('/Acknowledgement')
    def acknowledgement(self, request, tl, one, two, module, extra, prog):
        context = {'prog': prog}
        if request.method == 'POST':
            context['form'] = studentacknowledgementform_factory(prog)(request.POST)
            rt = RecordType.objects.get(name="studentacknowledgement")
            rec, created = Record.objects.get_or_create(user=request.user,
                                                        program=self.program,
                                                        event=rt)
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
        qo = Q(record__program=self.program, record__event__name="studentacknowledgement")
        if QObject is True:
            return {'studentacknowledgement': qo}

        student_list = ESPUser.objects.filter(qo).distinct()

        return {'studentacknowledgement': student_list }

    def studentDesc(self):
        return {'studentacknowledgement': """Students who have submitted the acknowledgement for the program"""}

    class Meta:
        proxy = True
        app_label = 'modules'
