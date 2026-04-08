import json
from unittest.mock import patch

from esp.program.tests import ProgramFrameworkTest
from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.users.models import Record


class OnSiteClassListTransactionTest(ProgramFrameworkTest):
    # simple setup callign of modules
    def setUp(self, *args, **kwargs):
        modules = [ProgramModule.objects.get(handler='OnSiteClassList')]
        kwargs.update({'modules': modules})
        super().setUp(*args, **kwargs)

        self.add_student_profiles()

        self.admin = self.admins[0]
        self.student = self.students[0]
        self.assertTrue(
            self.client.login(username=self.admin.username, password='password'),
            "Couldn't log in as admin %s" % self.admin.username
        )

        pm = ProgramModule.objects.get(handler='OnSiteClassList')
        self.module = ProgramModuleObj.getFromProgModule(self.program, pm)

    def get_register_url(self):
        return '/onsite/%s/register_student' % self.program.getUrlBase()

    def _count_onsite_bits(self):
        return Record.objects.filter(
            user=self.student,
            program=self.program,
            event__name__in=['attended', 'med', 'liab', 'onsite'],
        ).count()

    def test_register_student_success_sets_status_true(self):
        response = self.client.post(self.get_register_url(), {'student_id': str(self.student.id)})
        self.assertEqual(response.status_code, 200)

        payload = json.loads(response.content)
        self.assertTrue(payload['status'])

        self.assertEqual(self._count_onsite_bits(), 4)

    def test_register_student_rolls_back_if_createbit_fails_midway(self):
        original_create_bit = Record.createBit

        def flaky_create_bit(extension, program, user):
            if extension == 'med':
                raise RuntimeError('forced failure in createBit')
            return original_create_bit(extension, program, user)

        with patch('esp.program.modules.handlers.onsiteclasslist.Record.createBit', side_effect=flaky_create_bit):
            with self.assertRaises(RuntimeError):
                self.client.post(self.get_register_url(), {'student_id': str(self.student.id)})

        self.assertEqual(
            Record.objects.filter(
                user=self.student,
                program=self.program,
                event__name__in=['attended', 'med', 'liab', 'onsite'],
            ).count(),
            0
        )

    def test_register_student_rolls_back_if_updatepaid_fails(self):
        with patch(
            'esp.program.modules.handlers.onsiteclasslist.IndividualAccountingController.updatePaid',
            side_effect=RuntimeError('forced failure in updatePaid'),
        ):
            with self.assertRaises(RuntimeError):
                self.client.post(self.get_register_url(), {'student_id': str(self.student.id)})

        self.assertEqual(
            Record.objects.filter(
                user=self.student,
                program=self.program,
                event__name__in=['attended', 'med', 'liab', 'onsite'],
            ).count(),
            0
        )