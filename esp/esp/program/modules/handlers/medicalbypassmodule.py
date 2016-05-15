from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call
from esp.utils.web import render_to_response
from esp.users.models import Record
from esp.users.forms.generic_search_form import GenericSearchForm


class MedicalBypassModule(ProgramModuleObj):
    """Module for allowing users to bypass the FormstackMedliabModule"""

    @classmethod
    def module_properties(cls):
        return [{
                "admin_title": "Formstack Med-liab Bypass Page",
                "link_title": "Grant Medliab Bypass",
                "module_type": "manage",
                }]

    @main_call
    @needs_admin
    def medicalbypass(self, request, tl, one, two, module, extra, prog):
        status = None

        if request.method == 'POST':
            form = GenericSearchForm(request.POST)
            if form.is_valid():
                user = form.cleaned_data['target_user']
                if Record.objects.filter(user=user,
                                         program=self.program,
                                         event="med_bypass").exists():
                    status = 'bypass exists'
                elif Record.objects.filter(user=user,
                                           program=self.program,
                                           event="med").exists():
                    status = 'reg bit exists'
                else:
                    Record.objects.create(user=user,
                                          program=self.program,
                                          event="med_bypass")
                    status = 'success'
            else:
                status = 'invalid user'

        context = {'status': status, 'form': GenericSearchForm()}

        return render_to_response(self.baseDir()+'medicalbypass.html',
                                  request, context)
