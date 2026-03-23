__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2013 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@learningu.org
"""

from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.program.models import PhaseZeroRecord, RegistrationProfile
from esp.users.models import ESPUser, StudentInfo
from esp.tagdict.models import Tag
from django.contrib.auth.models import Group
from esp.users.models import Permission


class StudentRegPhaseZeroManageTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_students': 20,
            'grade_min': 7,
            'grade_max': 12,
        })
        super().setUp(*args, **kwargs)

        # Get the module
        pm = ProgramModule.objects.get(handler='StudentRegPhaseZeroManage')
        self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, pm)

        # Set up student profiles with grades
        self.add_student_profiles()

    def add_student_profiles(self):
        schoolyear = ESPUser.program_schoolyear(self.program)
        for i, student in enumerate(self.students):
            grade = 7 + (i % 6)  # grades 7 to 12
            yog = schoolyear + 12 - grade
            student_info, created = StudentInfo.objects.get_or_create(user=student, defaults={'graduation_year': yog})
            student_info.graduation_year = yog
            student_info.save()
            RegistrationProfile.objects.get_or_create(user=student, program=self.program, defaults={'student_info': student_info})

    def test_default_lottery_success(self):
        # Set grade caps
        Tag.setTag('program_size_by_grade', target=self.program, value='{"7-8": 2, "9-10": 2, "11-12": 2}')

        # Create PhaseZeroRecord for some students
        for i in range(10):
            rec = PhaseZeroRecord(program=self.program)
            rec.save()
            rec.user.add(self.students[i])

        # Run lottery in default mode
        post = {'mode': 'default', 'perms': 'on'}
        messages = self.moduleobj.lottery(self.program, str(self.program) + " Winner", post)

        # Check success
        self.assertEqual(len(messages['error']), 0)
        self.assertIn("The student lottery has been run successfully", messages['success'])

        # Check group created
        winners_group = Group.objects.get(name=str(self.program) + " Winner")
        self.assertTrue(winners_group.user_set.exists())

        # Check permissions
        perms = Permission.objects.filter(role=winners_group, program=self.program)
        self.assertTrue(perms.filter(permission_type='OverridePhaseZero').exists())
        self.assertTrue(perms.filter(permission_type='Student/All').exists())

        # Check tag
        self.assertTrue(Tag.getBooleanTag('student_lottery_run', self.program))

    def test_default_lottery_missing_grade_caps(self):
        # No grade caps set
        # Create PhaseZeroRecord
        rec = PhaseZeroRecord(program=self.program)
        rec.save()
        rec.user.add(self.students[0])

        post = {'mode': 'default'}
        messages = self.moduleobj.lottery(self.program, str(self.program) + " Winner", post)

        self.assertIn("program_size_by_grade", messages['error'][0])
        self.assertIn("is not set", messages['error'][0])

    def test_manual_lottery_valid_usernames(self):
        # Create PhaseZeroRecord
        rec = PhaseZeroRecord(program=self.program)
        rec.save()
        rec.user.add(self.students[0])

        post = {'mode': 'manual', 'usernames': self.students[0].username, 'perms': 'on'}
        messages = self.moduleobj.lottery(self.program, str(self.program) + " Winner", post)

        self.assertEqual(len(messages['error']), 0)
        self.assertIn("The student lottery has been run successfully", messages['success'])

        # Check group
        winners_group = Group.objects.get(name=str(self.program) + " Winner")
        self.assertIn(self.students[0], winners_group.user_set.all())

    def test_manual_lottery_invalid_username(self):
        post = {'mode': 'manual', 'usernames': 'invaliduser'}
        messages = self.moduleobj.lottery(self.program, str(self.program) + " Winner", post)

        self.assertIn("Could not find a user with username invaliduser", messages['error'][0])

    def test_manual_lottery_non_student(self):
        # Make a teacher
        teacher = self.teachers[0]
        post = {'mode': 'manual', 'usernames': teacher.username}
        messages = self.moduleobj.lottery(self.program, str(self.program) + " Winner", post)

        self.assertIn(teacher.username + " is not a student", messages['error'][0])

    def test_manual_lottery_not_in_lottery(self):
        student = self.students[0]
        post = {'mode': 'manual', 'usernames': student.username}
        messages = self.moduleobj.lottery(self.program, str(self.program) + " Winner", post)

        self.assertIn(student.username + " is not in the lottery", messages['error'][0])

    def test_unsupported_mode(self):
        post = {'mode': 'invalid'}
        messages = self.moduleobj.lottery(self.program, str(self.program) + " Winner", post)

        self.assertIn("Lottery mode invalid is not supported", messages['error'][0])