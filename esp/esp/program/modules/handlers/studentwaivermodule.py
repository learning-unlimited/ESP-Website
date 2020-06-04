from esp.program.models import Program
from esp.program.modules.base import ProgramModuleObj, needs_student, main_call, meets_deadline
from esp.utils.web import render_to_response
from esp.users.models   import ESPUser, Record
from django import forms
from django.db.models.query import Q
from esp.middleware.threadlocalrequest import get_current_request
from esp.tagdict.models import Tag

def studentwaiverform_factory(prog):
    name = "StudentWaiverForm"
    bases = (forms.Form,)
    date_range = prog.date_range()

    label_tag = Tag.getProgramTag('student_waiver_label', prog, default=None)
    if label_tag is not None:
        label = str(label_tag)
    else:
        label = u"I have completed the online liability waiver."

    d = dict(waiver=forms.BooleanField(required=True, label=label))
    return type(name, bases, d)

class StudentWaiverModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Student Waiver",
            "link_title": "Student Waiver",
            "module_type": "learn",
            "required": False,
        }

    def isCompleted(self):
        return Record.objects.filter(user=get_current_request().user,
                                     program=self.program,
                                     event="studentwaiver").exists()

    @main_call
    @needs_student
    @meets_deadline('/Waiver')
    def waiver(self, request, tl, one, two, module, extra, prog):
        context = {'prog': prog}
        if request.method == 'POST':
            context['form'] = studentwaiverform_factory(prog)(request.POST)
            rec, created = Record.objects.get_or_create(user=request.user,
                                                        program=self.program,
                                                        event="studentwaiver")
            if context['form'].is_valid():
                return self.goToCore(tl)
            else:
                rec.delete()
        elif self.isCompleted():
            context['form'] = studentwaiverform_factory(prog)({'waiver': True})
        else:
            context['form'] =studentwaiverform_factory(prog)()
        return render_to_response(self.baseDir()+'waiver.html', request, context)

    def students(self, QObject = False):
        """ Returns a list of students who have completed the liability waiver. """
        from datetime import datetime
        qo = Q(record__program=self.program, record__event="studentwaiver")
        if QObject is True:
            return {'waiver': qo}

        student_list = ESPUser.objects.filter(qo).distinct()

        return {'waiver': student_list }

    def studentDesc(self):
        return {'waiver': """Students who have completed the liability waiver for the program"""}

    class Meta:
        proxy = True
        app_label = 'modules'


