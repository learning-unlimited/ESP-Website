__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2014 by the individual contributors
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

import datetime

from esp.program.controllers.classreg import ClassCreationController
from esp.program.modules.base import ProgramModule, ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser, Record

class TeacherCheckinModuleTest(ProgramFrameworkTest):

    def setUp(self, *args, **kwargs):
        super(TeacherCheckinModuleTest, self).setUp(*args, **kwargs)
        self.add_user_profiles()
        self.schedule_randomly() # only scheduled classes used in module
        self.ccc      = ClassCreationController(self.program)
        pm            = ProgramModule.objects.get(handler='TeacherCheckinModule')
        self.module   = ProgramModuleObj.getFromProgModule(self.program, pm)
        self.now      = self.settings['start_time']
        self.past     = datetime.datetime(1970, 1, 1)
        self.future   = datetime.datetime.max
        self.admin    = self.admins[0]
        self.teacher  = self.teachers[0]
        self.cls      = self.teacher.getTaughtClasses()[0]
        self.event    = 'teacher_checked_in'
        self.teacher2 = ESPUser.objects.create(username='CheckinTeacher2')
        self.teacher2.makeRole("Teacher")

    def tearDown(self):
        Record.objects.filter(program=self.program, event=self.event).delete()
        super(TeacherCheckinModuleTest, self).tearDown()

    def addCoteacher(self, cls, coteacher):
        self.ccc.associate_teacher_with_class(cls, coteacher)

    # Aliases so full set of args don't need to be typed each time.
    # 'when' defaults to self.now (the datetime of the program), and
    # 'teacher' defaults to self.teacher.

    def isCheckedIn(self, when=None, teacher=None):
        if when is None:
            when = self.now
        if teacher is None:
            teacher = self.teacher
        return Record.user_completed(teacher, self.event, self.program,
                                     when, only_today=True)

    def checkIn(self, when=None, teacher=None):
        if when is None:
            when = self.now
        if teacher is None:
            teacher = self.teacher
        return self.module.checkIn(teacher, self.program, when)

    def undoCheckIn(self, when=None, teacher=None):
        if when is None:
            when = self.now
        if teacher is None:
            teacher = self.teacher
        return self.module.undoCheckIn(teacher, self.program, when)

    # End aliases.

    def test_checkIn(self):
        """Run tests for checkIn() and undoCheckIn()."""

        # Test that calling checkIn() works, and
        # that calling it again does nothing.
        self.assertFalse(self.isCheckedIn())
        self.assertIn('is checked in until', self.checkIn())
        self.assertTrue(self.isCheckedIn())
        self.assertIn('has already been checked in until', self.checkIn())
        self.assertTrue(self.isCheckedIn())

        # Test that checking in the teacher in the present has no effect on
        # check-in status in the past or future, and that checking in the
        # teacher in the future has no effect on check-in status in the
        # present or past.
        self.assertFalse(self.isCheckedIn(self.past))
        self.assertFalse(self.isCheckedIn(self.future))
        self.assertIn('is checked in until', self.checkIn(self.future))
        self.assertTrue(self.isCheckedIn())
        self.assertTrue(self.isCheckedIn(self.future))
        self.assertFalse(self.isCheckedIn(self.past))

        # Test that undoing check-in in the future has no effect on check-in
        # status in the present or past.
        self.assertIn('is no longer checked in.', self.undoCheckIn(self.future))
        self.assertFalse(self.isCheckedIn(self.future))
        self.assertTrue(self.isCheckedIn())
        self.assertFalse(self.isCheckedIn(self.past))

        # Test that calling undoCheckIn() works, and
        # that calling it again does nothing.
        self.assertIn('is no longer checked in.', self.undoCheckIn())
        self.assertFalse(self.isCheckedIn())
        self.assertIn('was not checked in for', self.undoCheckIn())
        self.assertFalse(self.isCheckedIn())

        # Test that you can't successfully call checkIn() or undoCheckIn()
        # for a user who is not teaching a class for the program.
        self.assertIn('is not a teacher for',
                      self.checkIn(teacher=self.teacher2))
        self.assertIn('was not checked in for',
                      self.undoCheckIn(teacher=self.teacher2))

    def test_phone_numbers_on_checkin_page(self):
        self.assertTrue(self.client.login(username=self.admin.username, password='password'), "Couldn't log in as admin %s" % self.admin.username)
        response = self.client.get(u'%smissingteachers' % self.program.get_onsite_url())
        phone = self.teacher.getLastProfile().contact_user.phone_cell
        self.assertIn(phone, response.content.decode('utf-8'))
