from __future__ import absolute_import
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call
from esp.utils.web import render_to_response
from esp.users.models import Record, RecordType
from esp.users.forms.generic_search_form import StudentSearchForm


class MedicalBypassModule(ProgramModuleObj):
    doc = """Module for allowing users to bypass the FormstackMedliabModule"""

    @classmethod
    def module_properties(cls):
        return {
                "admin_title": "Formstack Med-liab Bypass Page",
                "link_title": "Grant Medliab Bypass",
                "module_type": "manage",
                "seq": 3,
                "required": True,
                "choosable": 2,
                }

    @main_call
    @needs_admin
    def medicalbypass(self, request, tl, one, two, module, extra, prog):
        status = None

        if request.method == 'POST':
            form = StudentSearchForm(request.POST)
            if form.is_valid():
                user = form.cleaned_data['target_user']
                if Record.objects.filter(user=user,
                                         program=self.program,
                                         event__name="med_bypass").exists():
                    status = 'bypass exists'
                elif Record.objects.filter(user=user,
                                           program=self.program,
                                           event__name="med").exists():
                    status = 'reg bit exists'
                else:
                    rt = RecordType.objects.get(name="med_bypass")
                    Record.objects.create(user=user,
                                          program=self.program,
                                          event=rt)
                    status = 'success'
            else:
                status = 'invalid user'

        context = {'status': status, 'form': StudentSearchForm()}

        return render_to_response(self.baseDir()+'medicalbypass.html',
                                  request, context)

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'
