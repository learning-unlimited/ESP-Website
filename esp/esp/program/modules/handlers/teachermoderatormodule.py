from esp.program.models import ModeratorRecord
from esp.program.modules.base import ProgramModuleObj, needs_teacher, main_call, meets_deadline
from esp.program.modules.forms.moderate import ModeratorForm
from esp.users.models import ESPUser
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
        """ Returns lists of teachers who have offered or are assigned to moderate. """
        qw = Q(moderatorrecord__program=self.program, moderatorrecord__will_moderate=True)
        qa = Q(moderating_sections__parent_class__parent_program=self.program)
        if QObject is True:
            return {'will_moderate': qw, 'assigned_moderator': qa}

        offered_list = ESPUser.objects.filter(qw).distinct()
        assigned_list = ESPUser.objects.filter(qa).distinct()

        return {'will_moderate': offered_list,
                'assigned_moderator': assigned_list}

    def teacherDesc(self):
        return {'will_moderate': """Teachers who have also offered to moderate""",
                'assigned_moderator': """Teachers who are assigned as moderators"""}

    class Meta:
        proxy = True
        app_label = 'modules'


