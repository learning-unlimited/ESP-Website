from __future__ import absolute_import

from datetime import timedelta

from esp.program.models import ProgramModule, RegistrationType, StudentRegistration
from esp.program.modules.base import ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest


class OnSiteAttendanceTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.add_user_profiles()
        self.schedule_randomly()
        pm = ProgramModule.objects.get(handler='OnSiteAttendance')
        self.module = ProgramModuleObj.getFromProgModule(self.program, pm)
        self.attended, _ = RegistrationType.objects.get_or_create(
            name='Attended',
            category='student',
        )
        self.section = list(self.program.sections())[0]

    def test_times_attending_class_skips_invalid_time_windows(self):
        valid_student, invalid_student = self.students[:2]
        section_start = self.section.start_time().start

        StudentRegistration.objects.create(
            user=valid_student,
            section=self.section,
            relationship=self.attended,
            start_date=section_start,
        )
        StudentRegistration.objects.create(
            user=invalid_student,
            section=self.section,
            relationship=self.attended,
            start_date=section_start + timedelta(hours=4),
        )

        attendance = self.module.times_attending_class(self.program)
        expected_hour = section_start.replace(minute=0, second=0, microsecond=0)
        invalid_hour = (section_start + timedelta(hours=4)).replace(
            minute=0,
            second=0,
            microsecond=0,
        )

        self.assertEqual(attendance[expected_hour], [valid_student])
        self.assertNotIn(invalid_hour, attendance)
