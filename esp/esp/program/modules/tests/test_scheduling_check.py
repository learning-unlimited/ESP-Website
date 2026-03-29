from django.test import RequestFactory

from esp.middleware.threadlocalrequest import ThreadLocals, clear_current_request
from esp.program.modules.handlers.schedulingcheckmodule import (
    SchedulingCheckRunner,
    JSONFormatter,
)
from esp.program.modules.base import ProgramModuleObj
from esp.program.models import ProgramModule
from esp.program.tests import ProgramFrameworkTest
import json


class SchedulingCheckHelpersTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_timeslots': 2,
            'num_rooms': 3,
            'num_teachers': 2,
            'classes_per_teacher': 1,
            'sections_per_class': 1,
        })
        super().setUp(*args, **kwargs)

    def tearDown(self):
        clear_current_request()
        super().tearDown()

    def test_json_formatter_format_table_with_list_input(self):
        formatter = JSONFormatter()
        data = [{'a': 1, 'b': 2}, {'a': 3, 'b': 4}]
        result = formatter.format_table(data, {'headings': ['a', 'b']}, help_text='hi')

        parsed = json.loads(result)
        self.assertEqual(parsed['help_text'], 'hi')
        self.assertEqual(parsed['headings'], ['a', 'b'])
        self.assertEqual(parsed['body'], [[1, 2], [3, 4]])

    def test_json_formatter_format_table_with_dict_input(self):
        formatter = JSONFormatter()
        data = {'x': {'a': 10, 'b': 20}, 'y': {'a': 30, 'b': 40}}
        result = formatter.format_table(data, {'headings': ['a', 'b']}, help_text='ok')

        parsed = json.loads(result)
        self.assertEqual(parsed['help_text'], 'ok')
        self.assertEqual(parsed['headings'], ['', 'a', 'b'])
        self.assertEqual(parsed['body'][0][0], 'x')
        self.assertEqual(parsed['body'][1][0], 'y')

    def test_json_formatter_format_list(self):
        formatter = JSONFormatter()
        input_list = [10, 20, 30]
        result = formatter.format_list(input_list, ['value'], help_text='list')

        parsed = json.loads(result)
        self.assertEqual(parsed['help_text'], 'list')
        self.assertEqual(parsed['headings'], ['value'])
        self.assertEqual(parsed['body'], [[10], [20], [30]])

    def test_scheduling_check_runner_respects_unreviewed_get_flag(self):
        request = RequestFactory().get('/manage/%s/scheduling_checks' % self.program.getUrlBase(), {'unreviewed': '1'})
        request.user = self.admins[0]
        ThreadLocals().process_request(request)

        runner = SchedulingCheckRunner(self.program)
        self.assertTrue(runner.incl_unreview)

    def test_scheduling_checks_extra_key_returns_diagnostic_output(self):
        request = RequestFactory().get('/manage/%s/scheduling_checks' % self.program.getUrlBase())
        request.user = self.admins[0]
        request.session = {}
        ThreadLocals().process_request(request)

        pm = ProgramModule.objects.get(handler='SchedulingCheckModule')
        moduleobj = ProgramModuleObj.getFromProgModule(self.program, pm)

        response = moduleobj.scheduling_checks(request, 'manage', None, None, None, 'lunch_blocks_setup', self.program)

        self.assertEqual(response.status_code, 200)

        parsed = json.loads(response.content.decode('utf-8'))
        # Verify that the extra diagnostic key returns structured JSON output
        self.assertIn('headings', parsed)
        # The "lunch_blocks_setup" diagnostic should include a "Lunch Blocks" heading
        self.assertIn('Lunch Blocks', parsed['headings'])
