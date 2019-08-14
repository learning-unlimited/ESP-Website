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
    label = u"I have read the above, and I commit to satisfying the MIT minors policy."

    d = dict(
        backgroundcheck_choice = forms.ChoiceField(label='Background Checks', choices=[
            ('affiliated', 'I am a current MIT student, faculty, or staff.'),
            ('recent_check', 'I am not currently MIT-affiliated, but I have received an MIT background check in the past year.'),
            ('commit_check', 'I am not currently MIT-affiliated, and I will initiate a background check by Thursday, October 17.'),
        ], widget=BlankSelectWidget(),
                                        help_text='\n(The MIT Minors Policy requires that all non-MIT-affiliated teachers be background checked.)' , required=True),
        observing_choice = forms.ChoiceField(label='Coteaching or Observing', choices=[
            ('no', 'I have coteachers or commit to finding coteachers for all of my classes by the registration deadline.'),
            ('yes', "I agree to sit in on someone else's class for each of my classes without a coteacher."),
            ('other', 'Other: I will explain in an email to the directors at splash@mit.edu.'),
        ], widget=BlankSelectWidget(),
                                        help_text='\n(The MIT Minors Policy requires that all classes have at least 2 adults present at all times.)' , required=True),
    )
    return type(name, bases, d)

BACKGROUNDCHECK_CHOICE_PREFIX = "minorspolicy_"
OBSERVING_CHOICE_PREFIX = "observing_"

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
            backgroundcheck_selection = context['form']['backgroundcheck_choice'].data
            observing_selection = context['form']['observing_choice'].data
            rec, created = Record.objects.get_or_create(user=request.user,
                                                        program=self.program,
                                                        event="minorspolicyacknowledgement")
            # delete old choices
            Record.objects.filter(
                    user=get_current_request().user,
                    program=self.program,
                    event__startswith=BACKGROUNDCHECK_CHOICE_PREFIX).delete()
            Record.objects.filter(
                    user=get_current_request().user,
                    program=self.program,
                    event__startswith=OBSERVING_CHOICE_PREFIX).delete()
            # backgroundcheck_affiliated / backgroundcheck_recent_check / backgroundcheck_commit_check
            backgroundcheck_rec_type, _ = Record.objects.get_or_create(user=request.user,
                                                        program=self.program,
                                                        event=BACKGROUNDCHECK_CHOICE_PREFIX + backgroundcheck_selection)
            # observing_yes / observing_no / observing_other
            observing_rec_type, _ = Record.objects.get_or_create(user=request.user,
                                                        program=self.program,
                                                        event=OBSERVING_CHOICE_PREFIX + observing_selection)
            if context['form'].is_valid():
                return self.goToCore(tl)
            else:
                rec.delete()
                backgroundcheck_rec_type.delete()
                observing_rec_type.delete()
        elif self.isCompleted():
            backgroundcheck_choice_records = Record.objects.filter(
                    user=get_current_request().user,
                    program=self.program,
                    event__startswith=BACKGROUNDCHECK_CHOICE_PREFIX)

            backgroundcheck_choice = None
            if backgroundcheck_choice_records:
                backgroundcheck_choice = backgroundcheck_choice_records[0].event[len(BACKGROUNDCHECK_CHOICE_PREFIX):]

            observing_choice_records = Record.objects.filter(
                    user=get_current_request().user,
                    program=self.program,
                    event__startswith=OBSERVING_CHOICE_PREFIX)

            observing_choice = None
            if observing_choice_records:
                observing_choice = observing_choice_records[0].event[len(OBSERVING_CHOICE_PREFIX):]

            context['form'] = minorspolicyacknowledgementform_factory(prog)({
                'backgroundcheck_choice': backgroundcheck_choice,
                'observing_choice': observing_choice,
            })
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
