from esp.program.models import Program
from esp.program.modules.base import ProgramModuleObj, needs_teacher, main_call, meets_deadline
from esp.utils.web import render_to_response
from esp.users.models   import ESPUser, Record
from django import forms
from django.db.models.query import Q
from esp.middleware.threadlocalrequest import get_current_request
from esp.tagdict.models import Tag

def teacherwaiverform_factory(prog):
    name = "TeacherWaiverForm"
    bases = (forms.Form,)
    date_range = prog.date_range()

    label_tag = Tag.getProgramTag('teacher_waiver_label', prog, default=None)
    if label_tag is not None:
        label = str(label_tag)
    else:
        label = u"I have completed the online liability waiver."

    d = dict(waiver=forms.BooleanField(required=True, label=label))
    return type(name, bases, d)

class TeacherWaiverModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Teacher Waiver",
            "link_title": "Teacher Waiver",
            "module_type": "teach",
            "required": False,
        }

    def isCompleted(self):
        return Record.objects.filter(user=get_current_request().user,
                                     program=self.program,
                                     event="teacherwaiver").exists()

    @main_call
    @needs_teacher
    @meets_deadline('/Waiver')
    def waiver(self, request, tl, one, two, module, extra, prog):
        context = {'prog': prog}
        if request.method == 'POST':
            context['form'] = teacherwaiverform_factory(prog)(request.POST)
            rec, created = Record.objects.get_or_create(user=request.user,
                                                        program=self.program,
                                                        event="teacherwaiver")
            if context['form'].is_valid():
                return self.goToCore(tl)
            else:
                rec.delete()
        elif self.isCompleted():
            context['form'] = teacherwaiverform_factory(prog)({'waiver': True})
        else:
            context['form'] = teacherwaiverform_factory(prog)()
        return render_to_response(self.baseDir()+'waiver.html', request, context)

    def teachers(self, QObject = False):
        """ Returns a list of teachers who have completed the liability waiver. """
        from datetime import datetime
        qo = Q(record__program=self.program, record__event="teacherwaiver")
        if QObject is True:
            return {'waiver': qo}

        teacher_list = ESPUser.objects.filter(qo).distinct()

        return {'waiver': teacher_list }

    def teacherDesc(self):
        return {'waiver': """Teachers who have completed the liability waiver for the program"""}

    class Meta:
        proxy = True
        app_label = 'modules'


