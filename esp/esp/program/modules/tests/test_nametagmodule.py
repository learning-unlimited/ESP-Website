from django.test.client import RequestFactory

from esp.middleware import ESPError_NoLog
from esp.program.models import ProgramModule, RegistrationProfile
from esp.program.modules.base import ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.resources.models import Resource
from esp.tagdict.models import Tag
from esp.users.models import ESPUser


class NameTagModuleTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.add_user_profiles()

        pm = ProgramModule.objects.get(handler='NameTagModule')
        self.module = ProgramModuleObj.getFromProgModule(self.program, pm)
        self.rf = RequestFactory()
        self.url = '/manage/%s/generatetags' % self.program.url

    def _call_generatetags(self, data):
        request = self.rf.post(self.url, data=data)
        request.user = self.admins[0]
        request.session = {}
        return self.module.generatetags(request, 'manage', None, None, None, None, self.program)

    def _post_as_admin(self, data):
        self.assertTrue(self.client.login(username=self.admins[0].username, password='password'))
        data = dict(data, progname=self.program.niceName())
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        return response

    def _fronts(self, response):
        return [user for front, back in response.context['users_and_backs'] for user in front]

    def _set_pronouns(self, student, teacher):
        student_info = RegistrationProfile.getLastProfile(student).student_info
        student_info.pronoun = 'they/them'
        student_info.save()
        teacher_info = RegistrationProfile.getLastProfile(teacher).teacher_info
        teacher_info.pronoun = 'she/her'
        teacher_info.save()

    def test_nametag_data_structure(self):
        student, teacher = self.students[0], self.teachers[0]
        self._set_pronouns(student, teacher)

        users = self.module.nametag_data(
            ESPUser.objects.filter(id=student.id), 'Student',
            ESPUser.objects.filter(id=teacher.id), 'Teacher',
            program=self.program,
        )

        by_username = {u['username']: u for u in users}
        self.assertEqual(by_username, {
            student.username: {
                'title': 'Student',
                'name': '%s %s' % (student.first_name, student.last_name),
                'id': student.id,
                'username': student.username,
                'pronoun': 'they/them',
            },
            teacher.username: {
                'title': 'Teacher',
                'name': '%s %s' % (teacher.first_name, teacher.last_name),
                'id': teacher.id,
                'username': teacher.username,
                'pronoun': 'she/her',
            },
        })

    def test_nametag_data_hash_with_self_checkin_code(self):
        student = self.students[0]
        students = ESPUser.objects.filter(id=student.id)
        Tag.setTag('student_self_checkin', target=self.program, value='code')

        [with_program] = self.module.nametag_data(students, 'Student', program=self.program)
        self.assertEqual(with_program['hash'], student.userHash(self.program))

        [without_program] = self.module.nametag_data(students, 'Student')
        self.assertNotIn('hash', without_program)

    def test_nametag_data_skips_users_with_no_name(self):
        blank_user = ESPUser.objects.create(username='nametagblankuser', first_name='', last_name='')

        users = self.module.nametag_data(
            ESPUser.objects.filter(id__in=[self.students[0].id, blank_user.id]),
            'Student',
            program=self.program,
        )

        self.assertEqual([u['id'] for u in users], [self.students[0].id])

    def test_nametag_data_sort_by_time(self):
        early, late, unscheduled = self.teachers[1], self.teachers[0], self.teachers[2]
        for teacher, slot in ((early, 0), (late, 2)):
            section = self.program.sections().filter(parent_class__teachers=teacher).first()
            section.assign_meeting_times([self.timeslots[slot]])
            section.assign_room(Resource.objects.get(name='Room 0', event=self.timeslots[slot]))

        users = self.module.nametag_data(
            ESPUser.objects.filter(id__in=[late.id, unscheduled.id, early.id]),
            'Teacher',
            program=self.program,
            sort_by_time=True,
        )

        self.assertEqual([u['id'] for u in users], [early.id, late.id, unscheduled.id])

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

    def test_generatetags_students_only_includes_enrolled(self):
        enrolled = self.students[0]
        self.program.sections().first().preregister_student(enrolled, fast_force_create=True)

        response = self._post_as_admin({'type': 'students', 'barcodes': 'on'})

        self.assertTrue(response.context['barcodes'])
        self.assertContains(response, self.program.niceName())
        # One enrolled student is padded with blanks to a single six-tag page
        [(front, back)] = response.context['users_and_backs']
        self.assertEqual(len(front), 6)
        self.assertEqual(len(back), 6)
        self.assertEqual([u['id'] for u in front if u['id']], [enrolled.id])

    def test_generatetags_blank(self):
        response = self._post_as_admin({'type': 'blank', 'blanktitle': 'Guest', 'number': '3'})

        fronts = self._fronts(response)
        self.assertEqual(len(fronts), 6)
        self.assertTrue(all(u['title'] == 'Guest' and u['name'] == '' for u in fronts))

    def test_generatetags_misc_skips_malformed_lines(self):
        response = self._post_as_admin({
            'type': 'misc',
            'misc_info': 'Ada Lovelace, Speaker\nno comma here\nAlan Turing, Judge',
        })

        named = {u['name']: u['title'] for u in self._fronts(response) if u['name']}
        self.assertEqual(named, {'Ada Lovelace': 'Speaker', 'Alan Turing': 'Judge'})

    def test_generatetags_missing_type_raises(self):
        with self.assertRaises(ESPError_NoLog):
            self._call_generatetags({'progname': self.program.niceName()})

    def test_generatetags_other_missing_group_raises(self):
        for extra in ({'group': ''}, {}):
            with self.subTest(extra=extra), self.assertRaises(ESPError_NoLog):
                self._call_generatetags(dict(extra, type='other', blanktitle='Volunteer',
                                             progname=self.program.niceName()))

    def test_generatetags_blank_invalid_number_raises(self):
        for extra in ({'number': 'not-a-number'}, {}):
            with self.subTest(extra=extra), self.assertRaises(ESPError_NoLog):
                self._call_generatetags(dict(extra, type='blank', blanktitle='Guest',
                                             progname=self.program.niceName()))
