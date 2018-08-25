from esp.program.models import Program
from esp.program.modules.base import ProgramModuleObj, needs_teacher, main_call, meets_deadline
from esp.utils.widgets import BlankSelectWidget, SplitDateWidget
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

    d = dict(
        background_check  = forms.ChoiceField(label='Background Checks', choices=[
            ('mit', 'I am an MIT student, faculty, or staff.'),
            ('recent', 'I have received a background check in the past year.'),
            ('check', 'I commit to getting a background check.'),
        ], widget=BlankSelectWidget(),
                                        help_text='(The MIT Minors Policy requires that all non-MIT affiliated teachers be background checked.)' , required=True)
	)
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
            selection = context['form']['background_check']
            rec, created = Record.objects.get_or_create(user=request.user,
                                                        program=self.program,
                                                        event="minorspolicyacknowledgement")
            rec_type, _ = Record.objects.get_or_create(user=request.user,
                                                        program=self.program,
                                                        event='mit_affiliated' if selection == 'mit' else 'recent_background_check' if selection == 'recent' else 'commit_background_check' if selection == 'background_check' else 'error')
            if context['form'].is_valid():
                return self.goToCore(tl)
            else:
                rec.delete()
                rec_type.delete()
        elif self.isCompleted():
            # TODO: fill in with previously submitted data
            context['form'] = minorspolicyacknowledgementform_factory(prog)({'background_check': 'mit' if Record.objects.filter(user=get_current_request().user,
                                     program=self.program,
                                     event="mit_affiliated").exists() else 'recent' if Record.objects.filter(user=get_current_request().user,
                                     program=self.program,
                                     event="recent_background_check").exists() else 'commit' if Record.objects.filter(user=get_current_request().user,
                                     program=self.program,
                                     event="background_check").exists() else None})
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
