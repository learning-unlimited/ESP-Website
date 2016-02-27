import json
import random

from esp.program.models import ClassSection, StudentRegistration
from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser, Record

class UnenrollModuleTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_timeslots': 3, 'timeslot_length': 50, 'timeslot_gap': 10,
            'num_students': 30
        })
        super(UnenrollModuleTest, self).setUp(*args, **kwargs)

        self.add_student_profiles()
        self.schedule_randomly()
        self.classreg_students()

        # mark some of the students as checked in
        for student in random.sample(self.students, 10):
            Record.objects.create(
                event='attended', program=self.program, user=student)

        self.timeslots = self.program.getTimeSlots()

        pm = ProgramModule.objects.get(handler='UnenrollModule')
        self.module = ProgramModuleObj.getFromProgModule(self.program, pm)

        self.admin, created = ESPUser.objects.get_or_create(username='admin')
        self.admin.set_password('password')
        self.admin.makeAdmin()

    def test_page(self):
        self.client.login(username='admin', password='password')
        r = self.client.get('/onsite/' + self.program.url + '/unenroll_students')
        self.assertContains(r, "Select Students to Unenroll")
        for timeslot in self.program.getTimeSlotList():
            self.assertContains(r, timeslot.short_description)

    def test_json_view(self):
        self.client.login(username='admin', password='password')
        r = self.client.get('/onsite/' + self.program.url + '/unenroll_status')
        data = json.loads(r.content)

        self.assertGreaterEqual(len(data['student_timeslots']), 20)
        self.assertGreater(len(data['section_timeslots']), 0)
        self.assertGreater(len(data['enrollments']), 0)

        for student_id, ts_id in data['student_timeslots'].items():
            self.assertTrue(self.timeslots.filter(id=ts_id).exists())
            self.assertTrue(StudentRegistration.valid_objects().filter(
                user=student_id, section__meeting_times=ts_id).exists())
            self.assertFalse(Record.objects.filter(
                event='attended', program=self.program,
                user=student_id).exists())

        for section_id, ts_id in data['section_timeslots'].items():
            self.assertTrue(self.timeslots.filter(id=ts_id).exists())
            sec = ClassSection.objects.get(id=section_id)
            self.assertTrue(sec.meeting_times.filter(id=ts_id).exists())
            self.assertTrue(StudentRegistration.valid_objects().filter(
                section=section_id).exists())

        for sr_id, (user_id, section_id) in data['enrollments'].items():
            sr = StudentRegistration.objects.get(id=sr_id)
            self.assertEqual(sr.user_id, user_id)
            self.assertEqual(sr.section_id, section_id)
            self.assertIn(str(user_id), data['student_timeslots'])
            self.assertIn(str(section_id), data['section_timeslots'])

    def test_submit(self):
        self.client.login(username='admin', password='password')
        r = self.client.get('/onsite/' + self.program.url + '/unenroll_status')
        data = json.loads(r.content)
        enrollment_ids = data['enrollments'].keys()

        r = self.client.post('/onsite/' + self.program.url + '/unenroll_students', {'selected_enrollments': ','.join(enrollment_ids)})
        self.assertContains(r, 'Expired %d student registrations' % len(enrollment_ids))
        self.assertContains(r, ', '.join(enrollment_ids))

        enrollments = StudentRegistration.objects.filter(id__in=enrollment_ids)
        self.assertFalse(enrollments.filter(StudentRegistration.is_valid_qobject()).exists())

        enrollments.update(end_date=None)
