from esp.program.models import Program
from esp.program.modules.base import ProgramModuleObj, needs_teacher, main_call, meets_deadline
from esp.utils.web import render_to_response
from esp.users.models   import ESPUser, Record
from django import forms
from django.db.models.query import Q
from esp.middleware.threadlocalrequest import get_current_request

def minorspolicyacknowledgementform_factory(prog):
    name = "MinorsPolicyAcknowledgementForm"
    bases = (forms.Form,)
    date_range = prog.date_range()
    label = u"I have read the above, and commit to satisfy the MIT Minors policy."

    d = dict(acknowledgement=forms.BooleanField(required=True, label=label))
    return type(name, bases, d)

# The module name is limited to length 32. Whoops.
class MinorsPolicyModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Minors Policy Acknowledgement",
            "link_title": "Minors Policy Acknowledgement",
            "module_type": "teach",
            "required": False,
        }

    def isCompleted(self):
        return Record.objects.filter(user=get_current_request().user,
                                     program=self.program,
                                     event="minorspolicyacknowledgement").exists()

    @main_call
    @needs_teacher
    @meets_deadline('/Acknowledgement')
    def minorspolicyacknowledgement(self, request, tl, one, two, module, extra, prog):
        context = {'prog': prog}
        if request.method == 'POST':
            context['form'] = minorspolicyacknowledgementform_factory(prog)(request.POST)
            rec, created = Record.objects.get_or_create(user=request.user,
                                                        program=self.program,
                                                        event="minorspolicyacknowledgement")
            if context['form'].is_valid():
                return self.goToCore(tl)
            else:
                rec.delete()
        elif self.isCompleted():
            context['form'] = minorspolicyacknowledgementform_factory(prog)({'acknowledgement': True})
        else:
            context['form'] = minorspolicyacknowledgementform_factory(prog)()
        return render_to_response(self.baseDir()+'minorspolicyacknowledgement.html', request, context)

    def teachers(self, QObject = False):
        """ Returns a list of teachers who have submitted the acknowledgement. """
        from datetime import datetime
        qo = Q(record__program=self.program, record__event="minorspolicyacknowledgement")
        if QObject is True:
            return {'minorspolicyacknowledgement': qo}

        teacher_list = ESPUser.objects.filter(qo).distinct()

        return {'minorspolicyacknowledgement': teacher_list }

    def teacherDesc(self):
        return {'minorspolicyacknowledgement': """Teachers who have submitted the minors policy acknowledgement for the program."""}

    class Meta:
        proxy = True
        app_label = 'modules'
