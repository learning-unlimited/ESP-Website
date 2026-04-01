from django.test.client import RequestFactory

from esp.middleware import ESPError
from esp.program.models import ProgramModule, RegistrationProfile
from esp.program.modules.base import ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.tagdict.models import Tag
from esp.users.models import ESPUser


class NameTagModuleTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        super(NameTagModuleTest, self).setUp(*args, **kwargs)
        self.add_user_profiles()

        pm = ProgramModule.objects.get(handler='NameTagModule')
        self.module = ProgramModuleObj.getFromProgModule(self.program, pm)
        self.rf = RequestFactory()

    def _post_request(self, data, user):
        request = self.rf.post('/manage/%s/generatetags' % self.program.url, data=data)
        request.user = user
        request.session = {}
        return request

    def test_nametag_data_pronouns_and_hash(self):
        student = self.students[0]
        teacher = self.teachers[0]

        student_profile = RegistrationProfile.getLastProfile(student)
        student_profile.student_info.pronoun = 'they/them'
        student_profile.student_info.save()

        teacher_profile = RegistrationProfile.getLastProfile(teacher)
        teacher_profile.teacher_info.pronoun = 'she/her'
        teacher_profile.teacher_info.save()

        Tag.setTag('student_self_checkin', target=self.program, value='code')

        users = self.module.nametag_data(
            ESPUser.objects.filter(id=student.id),
            'Student',
            ESPUser.objects.filter(id=teacher.id),
            'Teacher',
            program=self.program,
        )

        self.assertEqual(len(users), 2)
        by_username = {u['username']: u for u in users}

        self.assertEqual(by_username[student.username]['title'], 'Student')
        self.assertEqual(by_username[student.username]['pronoun'], 'they/them')
        self.assertIn('hash', by_username[student.username])

        self.assertEqual(by_username[teacher.username]['title'], 'Teacher')
        self.assertEqual(by_username[teacher.username]['pronoun'], 'she/her')
        self.assertIn('hash', by_username[teacher.username])

    def test_nametag_data_skips_users_with_no_name(self):
        blank_user, _ = ESPUser.objects.get_or_create(
            username='nametagblankuser',
            defaults={'first_name': '', 'last_name': '', 'email': 'blank@example.com'},
        )

        users = self.module.nametag_data(
            ESPUser.objects.filter(id__in=[self.students[0].id, blank_user.id]),
            'Student',
            program=self.program,
        )

        self.assertTrue(any(u['username'] == self.students[0].username for u in users))
        self.assertFalse(any(u['username'] == blank_user.username for u in users))

    def test_selectidoptions_admin_only(self):
        self.assertTrue(self.client.login(username=self.admins[0].username, password='password'))
        admin_response = self.client.get('/manage/%s/selectidoptions' % self.program.url)
        self.assertEqual(admin_response.status_code, 200)
        self.assertContains(admin_response, 'generate nametags')

        self.client.logout()
        self.assertTrue(self.client.login(username=self.students[0].username, password='password'))
        student_response = self.client.get('/manage/%s/selectidoptions' % self.program.url)
        self.assertEqual(student_response.status_code, 200)
        self.assertContains(student_response, 'you are not an administrator')

    def test_generatetags_students_valid_post(self):
        self.assertTrue(self.client.login(username=self.admins[0].username, password='password'))
        response = self.client.post('/manage/%s/generatetags' % self.program.url, {
            'type': 'students',
            'progname': self.program.niceName(),
            'barcodes': 'on',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.program.niceName())
        self.assertIn('users_and_backs', response.context)
        self.assertTrue(response.context['barcodes'])

    def test_generatetags_missing_type_raises(self):
        request = self._post_request({'progname': self.program.niceName()}, self.admins[0])
        with self.assertRaises(ESPError):
            self.module.generatetags(request, 'manage', None, None, None, None, self.program)

    def test_generatetags_other_missing_group_raises(self):
        request = self._post_request({
            'type': 'other',
            'blanktitle': 'Volunteer',
            'group': '',
            'progname': self.program.niceName(),
        }, self.admins[0])
        with self.assertRaises(ESPError):
            self.module.generatetags(request, 'manage', None, None, None, None, self.program)

    def test_generatetags_blank_invalid_number_raises(self):
        request = self._post_request({
            'type': 'blank',
            'blanktitle': 'Guest',
            'number': 'not-a-number',
            'progname': self.program.niceName(),
        }, self.admins[0])
        with self.assertRaises(ValueError):
            self.module.generatetags(request, 'manage', None, None, None, None, self.program)

    def test_generatetags_unknown_type_is_stable(self):
        request = self._post_request({
            'type': 'unknown',
            'progname': self.program.niceName(),
        }, self.admins[0])
        response = self.module.generatetags(request, 'manage', None, None, None, None, self.program)
        self.assertEqual(response.status_code, 200)
