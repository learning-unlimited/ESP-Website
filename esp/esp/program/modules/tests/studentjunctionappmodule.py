# -*- coding: utf-8 -*-
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2026 by the individual contributors
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

from esp.program.tests import ProgramFrameworkTest
from esp.program.models.app_ import StudentAppQuestion, StudentApplication, StudentAppResponse
from esp.program.modules.handlers.studentjunctionappmodule import StudentJunctionAppModule
from django.db.models import Q

class StudentJunctionAppModuleTest(ProgramFrameworkTest):
      def setUp(self, *args, **kwargs):
                super().setUp(*args, **kwargs)
                self.add_student_profiles()

        # Initialize the module
                # Pre-fetch modules to get the handler instance
                self.pmo_module = None
                for mod in self.program.getModules():
                              if isinstance(mod, StudentJunctionAppModule):
                                                self.pmo_module = mod
                                                break

                          if not self.pmo_module:
                                        # Create it if not present
                                        from esp.program.models import ProgramModule
                                        mod_info, _ = ProgramModule.objects.get_or_create(
                                            link_title="Extra Application Info",
                                            admin_title="Extra Application Info (StudentJunctionAppModule)",
                                            module_type="learn",
                                            handler="StudentJunctionAppModule",
                                            seq=10000,
                                            choosable=True
                                        )
                                        self.program.program_modules.add(mod_info)
                                        # Re-fetch modules to get the instance
                                        for mod in self.program.getModules():
                                                          if isinstance(mod, StudentJunctionAppModule):
                                                                                self.pmo_module = mod
                                                                                break

                                                  self.assertIsNotNone(self.pmo_module, "StudentJunctionAppModule should be present in the program")

            def test_students_queryset_helpers(self):
                      """Test the students() queryset helper methods."""
                      # Ensure self.pmo_module is not None for type checkers
                      if self.pmo_module is None:
                                    self.fail("self.pmo_module is None")

                      student = self.students[0]
                      app = student.getApplication(self.program)

        # Test studentapps (all who started)
        results = self.pmo_module.students()
        self.assertIn(student, results['studentapps'])
        self.assertNotIn(student, results['studentapps_complete'])

        # Mark as complete
        app.done = True
        app.save()

        results = self.pmo_module.students()
        self.assertIn(student, results['studentapps'])
        self.assertIn(student, results['studentapps_complete'])

        # Test with QObject=True
        q_results = self.pmo_module.students(QObject=True)
        self.assertIsInstance(q_results['studentapps'], Q)

        from esp.users.models import ESPUser
        self.assertIn(student, ESPUser.objects.filter(q_results['studentapps']))

    def test_is_completed_marked_done(self):
              """isCompleted() should return True if the application is marked done."""
              if self.pmo_module is None:
                            self.fail("self.pmo_module is None")

              student = self.students[0]
              app = student.getApplication(self.program)
              app.done = True
              app.save()

        self.assertTrue(self.pmo_module.isCompleted(student))

    def test_is_completed_no_questions(self):
              """isCompleted() should return True if there are no questions."""
              if self.pmo_module is None:
                            self.fail("self.pmo_module is None")

              student = self.students[0]
              # Ensure no questions for this student
              StudentAppQuestion.objects.filter(program=self.program).delete()
        StudentAppQuestion.objects.filter(subject__parent_program=self.program).delete()

        # Trigger question setting
        student.getApplication(self.program).set_questions()
        self.assertTrue(self.pmo_module.isCompleted(student))

    def test_is_completed_partial_overlap(self):
              """isCompleted() should return False if not all questions are answered."""
              if self.pmo_module is None:
                            self.fail("self.pmo_module is None")

              student = self.students[0]
              # Create a program-level question
              q1 = StudentAppQuestion.objects.create(program=self.program, question="Test Q1")

        app = student.getApplication(self.program)
        app.set_questions()
        app.done = False
        app.save()

        # Initially not completed
        self.assertFalse(self.pmo_module.isCompleted(student))

        # Answer it
        resp = StudentAppResponse.objects.create(question=q1, response="Thinking...", complete=False)
        app.responses.add(resp)

        # Should be True because it has a response string
        self.assertTrue(self.pmo_module.isCompleted(student))

        # If response is empty and not complete, it returns False
        resp.response = ""
        resp.save()
        self.assertFalse(self.pmo_module.isCompleted(student))

        # If it's complete, it returns True even if response is empty
        resp.complete = True
        resp.save()
        self.assertTrue(self.pmo_module.isCompleted(student))

    def test_is_completed_per_class(self):
              """isCompleted() should check questions for applied classes."""
              if self.pmo_module is None:
                            self.fail("self.pmo_module is None")

              student = self.students[1]
              cls = self.program.classes()[0]
              sec = cls.get_sections()[0]
              sec.preregister_student(student)

        q_class = StudentAppQuestion.objects.create(subject=cls, question="Class Q")

        app = student.getApplication(self.program)
        app.set_questions()
        app.done = False
        app.save()

        self.assertFalse(self.pmo_module.isCompleted(student))

        # Answer it
        resp = StudentAppResponse.objects.create(question=q_class, response="I love chairs", complete=True)
        app.responses.add(resp)

        self.assertTrue(self.pmo_module.isCompleted(student))

    def test_main_view_rendering(self):
              """Test the application view rendering."""
              student = self.students[2]
              self.client.login(username=student.username, password='password')

        url = '/learn/%s/application' % self.program.url
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Extra Application Info")
