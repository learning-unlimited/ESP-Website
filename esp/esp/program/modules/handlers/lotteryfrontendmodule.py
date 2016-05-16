from esp.program.models import Program, ClassSection
from esp.program.modules.base import ProgramModuleObj, needs_admin, main_call, aux_call
from esp.program.controllers.lottery import LotteryAssignmentController, LotteryException
from esp.utils.web import render_to_response
from esp.users.models import ESPUser
from esp.utils.decorators import json_response
import numpy

class LotteryFrontendModule(ProgramModuleObj):

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Lottery Frontend",
            "link_title": "Run the Lottery Assignment Thing",
            "module_type": "manage",
            "seq": 10
            }

    @main_call
    @needs_admin
    def lottery(self, request, tl, one, two, module, extra, prog):
        #   Check that the lottery module is included
        students = self.program.students()
        if 'lotteried_students' not in students and 'twophase_star_students' not in students:
            return render_to_response(self.baseDir() + 'not_configured.html', request, {'program': prog})

        #   Render control page with lottery options
        context = {'options': {k: v for k, v in LotteryAssignmentController.default_options.items() if v[1] is not False}}
        return render_to_response(self.baseDir()+'lottery.html', request, context)

    def is_float(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    @aux_call
    @json_response()
    @needs_admin
    def lottery_execute(self, request, tl, one, two, module, extra, prog):
        # find what options the user wants
        options = {}

        for key in request.POST:
            if 'lottery_' in key:
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

        error_msg = ''
        try:
            lotteryObj = LotteryAssignmentController(prog, **options)
        except LotteryException, e:
            return {'response': [{'error_msg': str(e)}]}

        try:
            lotteryObj.compute_assignments(True)
        except LotteryException, e:
            return {'response': [{'error_msg': str(e)}]}

        stats = lotteryObj.extract_stats(lotteryObj.compute_stats())
        lottery_data = lotteryObj.export_assignments()
        return {'response': [{'stats': stats, 'lottery_data': lottery_data}]}

    @aux_call
    @json_response()
    @needs_admin
    def lottery_save(self, request, tl, one, two, module, extra, prog):
        if 'lottery_data' not in request.POST:
            return {'response': [{'success': 'no', 'error': 'missing lottery_data POST field'}]};

        lotteryObj = LotteryAssignmentController(prog)
        lotteryObj.import_assignments(request.POST['lottery_data'])
        lotteryObj.save_assignments()
        return {'response': [{'success': 'yes'}]};

    @aux_call
    @json_response()
    @needs_admin
    def lottery_clear(self, request, tl, one, two, module, extra, prog):
        lotteryObj = LotteryAssignmentController(prog)
        lotteryObj.clear_saved_assignments()
        return {'response': [{'success': 'yes'}]};

    class Meta:
        proxy = True
        app_label = 'modules'
