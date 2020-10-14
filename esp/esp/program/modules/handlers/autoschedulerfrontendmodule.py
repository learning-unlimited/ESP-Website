import json

from esp.program.modules.base import \
    ProgramModuleObj, needs_admin, main_call, aux_call
from esp.program.controllers.autoscheduler.controller import \
    AutoschedulerController
from esp.program.controllers.autoscheduler.exceptions import \
    SchedulingError
from esp.utils.web import render_to_response
from esp.utils.decorators import json_response


class AutoschedulerFrontendModule(ProgramModuleObj):

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Autoscheduler Frontend",
            "link_title": "Use the automatic scheduling tool",
            "module_type": "manage",
            "seq": 50,
            "choosable": 2,
            }

    @main_call
    @needs_admin
    def autoscheduler(self, request, tl, one, two, module, extra, prog):

        #   Render control page with autoscheduler options
        try:
            context = {
                'constraints': AutoschedulerController.constraint_options(
                    prog),
                "scorers": AutoschedulerController.scorer_options(prog),
                "resources": AutoschedulerController.resource_options(prog),
                "search": AutoschedulerController.search_options(
                    prog, section=request.GET.get("section", None)),
                "program": prog
            }
            return render_to_response(
                self.baseDir()+'autoscheduler.html', request, context)
        except SchedulingError as e:
            context = {
                "program": prog,
                "err_msg": str(e)
            }
            return render_to_response(
                self.baseDir()+'error.html', request, context)

    def is_float(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    @aux_call
    @json_response()
    @needs_admin
    def autoscheduler_execute(
            self, request, tl, one, two, module, extra, prog):
        # find what options the user wants
        options = {}

        for key in request.POST:
            if 'autoscheduler_' in key:
                value = request.POST[key]

                if value == 'True':
                    value = True
                elif value == 'False':
                    value = False
                elif value == 'None':
                    value = None
                elif self.is_float(value):
                    value = float(value)

                options[key.split('_', 1)[1]] = value

        try:
            schedulerObj = AutoschedulerController(prog, **options)
            schedulerObj.compute_assignments()
        except (SchedulingError, ValueError), e:
            return {'response': [{'error_msg': str(e)}]}

        info = schedulerObj.get_scheduling_info()
        autoscheduler_data = json.dumps(schedulerObj.export_assignments())
        return {
            'response':
            [{'info': info, 'autoscheduler_data': autoscheduler_data}]}

    @aux_call
    @json_response()
    @needs_admin
    def autoscheduler_save(self, request, tl, one, two, module, extra, prog):
        if 'autoscheduler_data' not in request.POST:
            return {'response': [
                {'error_msg': 'missing autoscheduler_data POST field'}]}

        data, options = json.loads(request.POST['autoscheduler_data'])
        try:
            schedulerObj = AutoschedulerController(prog, **options)
            schedulerObj.import_assignments(data)
            schedulerObj.save_assignments()
        except SchedulingError, e:
            return {'response': [{'error_msg': str(e)}]}
        return {'response': [{'success': 'yes'}]}

    @aux_call
    @json_response()
    @needs_admin
    def autoscheduler_clear(self, request, tl, one, two, module, extra, prog):
        return {'response': [{'success': 'yes'}]}

    class Meta:
        proxy = True
        app_label = 'modules'
