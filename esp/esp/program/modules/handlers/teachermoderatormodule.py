from esp.program.models import ModeratorRecord
from esp.program.modules.base import ProgramModuleObj, needs_teacher, main_call, meets_deadline
from esp.program.modules.forms.moderate import ModeratorForm
from esp.utils.web import render_to_response
from django.db.models.query import Q
from esp.middleware.threadlocalrequest import get_current_request

class TeacherModeratorModule(ProgramModuleObj):
    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Moderator Signup",
            "link_title": "Moderator Signup",
            "module_type": "teach",
            "required": True,
            'seq': 2,
            'choosable': 0,
        }

    def isCompleted(self):
        return ModeratorRecord.objects.filter(user=get_current_request().user, program=self.program).exists()

    @main_call
    @needs_teacher
    @meets_deadline('/Moderate')
    def moderate(self, request, tl, one, two, module, extra, prog):
        context = {'prog': prog}
        recs = ModeratorRecord.objects.filter(user=get_current_request().user, program=self.program)
        if request.method == 'POST':
            if recs.exists():
                form = ModeratorForm(request.POST, instance = recs[0], program = prog)
            else:
                form = ModeratorForm(request.POST, program = prog)
            if form.is_valid():
                modrec = form.save(commit = False)
                modrec.user = request.user
                modrec.program = prog
                modrec.save()
                form.save_m2m()
                return self.goToCore(tl)
            else:
                context['form'] = form
        else:
            if recs.exists():
                context['form'] = ModeratorForm(program = prog, instance = recs[0])
            else:
                context['form'] = ModeratorForm(program = prog)
        return render_to_response(self.baseDir()+'moderate.html', request, context)

    def teachers(self, QObject = False):
        """ Returns a list of teachers who have signed up to moderate. """
        from datetime import datetime
        qo = Q(moderatorrecord__program=self.program, will_moderate=True)
        if QObject is True:
            return {'moderator': qo}

        teacher_list = ESPUser.objects.filter(qo).distinct()

        return {'moderator': teacher_list }

    def teacherDesc(self):
        return {'moderator': """Teachers who have also signed up to moderate"""}

    class Meta:
        proxy = True
        app_label = 'modules'


