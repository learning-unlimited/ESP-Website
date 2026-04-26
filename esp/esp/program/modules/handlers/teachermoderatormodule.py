from __future__ import absolute_import
from esp.program.models import ModeratorRecord
from esp.program.modules.base import ProgramModuleObj, needs_teacher, main_call, meets_deadline, needs_admin, aux_call
from esp.program.modules.forms.moderate import ModeratorForm
from esp.tagdict.models import Tag
from esp.users.models import ESPUser
from esp.utils.web import render_to_response
from django.db.models.query import Q
from esp.middleware.threadlocalrequest import get_current_request

class TeacherModeratorModule(ProgramModuleObj):
    doc = """Adds a form to teacher registration allowing teachers to sign up as section moderators (also adds moderator features elsewhere on the site)."""

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
        if hasattr(self, 'user'):
            user = self.user
        else:
            user = get_current_request().user
        return ModeratorRecord.objects.filter(user=user, program=self.program).exists()

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
        return {'will_moderate': """Teachers who have also offered to be a """ + Tag.getProgramTag("moderator_title", self.program).lower(),
                'assigned_moderator': """Teachers who are assigned as """ + Tag.getProgramTag("moderator_title", self.program).lower() + """s"""}

    @aux_call
    @needs_admin
    def moderatorlookup(self, request, tl, one, two, module, extra, prog):

        # Search for teachers with names that start with search string
        if not 'name' in request.GET or 'name' in request.POST:
            return self.goToCore(tl)

        return self.moderatorlookup_logic(request, tl, one, two, module, extra, prog)

    @staticmethod
    def moderatorlookup_logic(request, tl, one, two, module, extra, prog, newclass = None):
        limit = 10
        from esp.web.views.json_utils import JsonResponse

        queryset = prog.teachers()['will_moderate']

        if not 'name' in request.GET:
            startswith = request.POST['name']
        else:
            startswith = request.GET['name']
        s = ''
        spaces = ''
        after_comma = False
        for char in startswith:
            if char == ' ':
                if not after_comma:
                    spaces += ' '
            elif char == ',':
                s += ','
                spaces = ''
                after_comma = True
            else:
                s += spaces + char
                spaces = ''
                after_comma = False
        startswith = s
        parts = [x.strip('*') for x in startswith.split(',')]

        #   Don't return anything if there's no input.
        if len(parts[0]) > 0:
            Q_name = Q(last_name__istartswith=parts[0])

            if len(parts) > 1:
                Q_name = Q_name & Q(first_name__istartswith=parts[1])

            # Isolate user objects
            queryset = queryset.filter(Q_name)[:(limit*10)]
            user_dict = {}
            for user in queryset:
                user_dict[user.id] = user
            users = list(user_dict.values())

            # Construct combo-box items
            obj_list = [{'name': "%s, %s" % (user.last_name, user.first_name), 'username': user.username, 'id': user.id} for user in users]
        else:
            obj_list = []

        return JsonResponse(obj_list)

    class Meta:
        proxy = True
        app_label = 'modules'


