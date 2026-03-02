from esp.program.tests import ProgramFrameworkTest
from esp.program.models import ClassSubject, ClassSection, StudentRegistration, RegistrationType
import json

class Issue561Test(ProgramFrameworkTest):
    def setUp(self):
        super().setUp()
        self.add_user_profiles()

        # Ensure we have at least 2 classes in the same timeslot
        ts = self.timeslots[0]
        # Get all classes in the program
        classes = list(self.program.classes())
        self.class1 = classes[0]
        self.class2 = classes[1]

        self.sec1 = self.class1.get_sections()[0]
        self.sec2 = self.class2.get_sections()[0]

        # Clear meeting times and set both to the same slot
        self.sec1.meeting_times.clear()
        self.sec1.meeting_times.add(ts)
        self.sec2.meeting_times.clear()
        self.sec2.meeting_times.add(ts)

        self.student = self.students[0]
        self.client.login(username=self.student.username, password='password')

    def test_ajax_addclass_conflict_resolution(self):
        # 1. Enroll in class 1
        self.sec1.preregister_student(self.student)
        self.assertEqual(len(list(self.student.getEnrolledSections(self.program))), 1)

        # 2. Attempt to enroll in class 2 via AJAX (should return script for confirmation)
        url = '/learn/%s/ajax_addclass' % self.program.url
        data = {
            'class_id': self.class2.id,
            'section_id': self.sec2.id,
        }
        response = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        resp_json = json.loads(response.content)

        # Verify it returns a script with a confirmation message
        self.assertIn('script', resp_json)
        self.assertIn('confirm', resp_json['script'])
        self.assertIn(str(self.class1.title), resp_json['script'])

        # 3. Simulate confirmation by sending force_replace=true
        data['force_replace'] = 'true'
        response = self.client.post(url, data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        # 4. Verify class 1 is dropped and class 2 is added
        enrolled_sections = list(self.student.getEnrolledSections(self.program))
        self.assertEqual(len(enrolled_sections), 1)
        self.assertEqual(enrolled_sections[0].id, self.sec2.id)
