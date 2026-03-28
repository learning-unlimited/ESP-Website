from esp.program.tests import ProgramFrameworkTest

import json
import random


class LotteryStudentRegAuthTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_timeslots': 3, 'timeslot_length': 50, 'timeslot_gap': 10,
            'num_teachers': 6, 'classes_per_teacher': 1, 'sections_per_class': 2,
            'num_rooms': 6,
        })
        super().setUp(*args, **kwargs)

        self.add_student_profiles()
        self.schedule_randomly()

    def expect_template(self, response, template):
        template_names = [tpl.name for tpl in response.templates if tpl.name]
        self.assertIn(
            template, template_names,
            'Wrong template for lottery view: got %s, expected %s'
            % (template_names, template),
        )

    def test_lottery(self):
        program = self.program
        teacher = random.choice(self.teachers)
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username,
        )

        response = self.client.get('/learn/%s/lotterystudentreg' % program.getUrlBase())

        self.expect_template(response, 'errors/program/notastudent.html')

    def test_lottery_submit_rejects_non_students_with_json(self):
        program = self.program
        teacher = random.choice(self.teachers)
        self.assertTrue(
            self.client.login(username=teacher.username, password='password'),
            "Couldn't log in as teacher %s" % teacher.username,
        )

        response = self.client.post(
            '/learn/%s/lsr_submit' % program.getUrlBase(),
            {'json_data': '{}'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn('application/json', response['Content-Type'])
        self.assertEqual(
            json.loads(str(response.content, encoding='UTF-8')),
            {'message': 'The user account is not a student.'},
        )

    def test_lottery_submit_accepts_student_ajax(self):
        program = self.program
        student = random.choice(self.students)
        self.assertTrue(
            self.client.login(username=student.username, password='password'),
            "Couldn't log in as student %s" % student.username,
        )

        response = self.client.post(
            '/learn/%s/lsr_submit' % program.getUrlBase(),
            {'json_data': '{}'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('application/json', response['Content-Type'])
        self.assertEqual(json.loads(str(response.content, encoding='UTF-8')), [])
