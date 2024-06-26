from __future__ import absolute_import
from esp.program.modules.base import ProgramModuleObj, needs_teacher, main_call, meets_deadline
from esp.utils.web import render_to_response
from esp.users.models   import ESPUser, Record, RecordType
from django import forms
from django.db.models.query import Q
from esp.middleware.threadlocalrequest import get_current_request
import six

def teacheracknowledgementform_factory(prog):
    name = "TeacherAcknowledgementForm"
    bases = (forms.Form,)
    date_range = prog.date_range()

    if prog.hasModule("TeacherModeratorModule"):
        teach_text = "teacher and/or " + prog.getModeratorTitle().lower()
    else:
        teach_text = "teacher"

    if date_range is None:
        label = six.u("I have read the above and commit to serving as a %s for my %s class(es).") % (teach_text, prog.program_type)
    else:
        label = six.u("I have read the above and commit to serving as a %s for my %s class(es) on %s.") % (teach_text, prog.program_type, date_range)

    d = dict(acknowledgement=forms.BooleanField(required=True, label=label))
    return type(name, bases, d)

class TeacherAcknowledgementModule(ProgramModuleObj):
    doc = """Serves a form asking teachers to acknowledge some agreement."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Teacher Acknowledgement",
            "link_title": "Teacher Acknowledgement",
            "module_type": "teach",
            "required": True,
            'choosable': 1,
        }

    def isCompleted(self):
        if hasattr(self, 'user'):
            user = self.user
        else:
            user = get_current_request().user
        return Record.objects.filter(user=user,
                                     program=self.program,
                                     event__name="teacheracknowledgement").exists()

    @main_call
    @needs_teacher
    @meets_deadline('/Acknowledgement')
    def acknowledgement(self, request, tl, one, two, module, extra, prog):
        context = {'prog': prog}
        if request.method == 'POST':
            context['form'] = teacheracknowledgementform_factory(prog)(request.POST)
            rt = RecordType.objects.get(name="teacheracknowledgement")
            rec, created = Record.objects.get_or_create(user=request.user,
                                                        program=self.program,
                                                        event=rt)
            if context['form'].is_valid():
                return self.goToCore(tl)
            else:
                rec.delete()
        elif self.isCompleted():
            context['form'] = teacheracknowledgementform_factory(prog)({'acknowledgement': True})
        else:
            context['form'] = teacheracknowledgementform_factory(prog)()
        return render_to_response(self.baseDir()+'acknowledgement.html', request, context)

    def teachers(self, QObject = False):
        """ Returns a list of teachers who have submitted the acknowledgement. """
        qo = Q(record__program=self.program, record__event__name="teacheracknowledgement")
        if QObject is True:
            return {'acknowledgement': qo}

        teacher_list = ESPUser.objects.filter(qo).distinct()

        return {'acknowledgement': teacher_list }

    def teacherDesc(self):
        return {'acknowledgement': """Teachers who have submitted the acknowledgement for the program"""}

    class Meta:
        proxy = True
        app_label = 'modules'


