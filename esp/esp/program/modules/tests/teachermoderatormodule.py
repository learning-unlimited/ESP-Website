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

import json
from unittest.mock import MagicMock
from django.test import RequestFactory
from esp.program.tests import ProgramFrameworkTest
from esp.program.models import ModeratorRecord, ProgramModule, ClassSection
from esp.program.modules.base import ProgramModuleObj
from esp.tagdict.models import Tag

class TeacherModeratorModuleTest(ProgramFrameworkTest):
    def setUp(self):
        super().setUp()
        self.add_user_profiles()
        m = ProgramModule.objects.get(handler='TeacherModeratorModule')
        # Setup module object for direct testing
        self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, m)

    def test_module_properties(self):
        """Test basic module metadata."""
        props = self.moduleobj.module_properties()
        self.assertEqual(props['admin_title'], "Moderator Signup")
        self.assertEqual(props['module_type'], "teach")

    def test_is_completed(self):
        """Test that isCompleted returns True only when a ModeratorRecord exists for the user and program."""
        teacher = self.teachers[0]
        self.moduleobj.user = teacher
        self.assertFalse(self.moduleobj.isCompleted())
        
        ModeratorRecord.objects.create(user=teacher, program=self.program, will_moderate=True, num_slots=1)
        self.assertTrue(self.moduleobj.isCompleted())

    def test_moderate_get_signup_form(self):
        """Test that a GET request to the moderator signup page renders the form."""
        teacher = self.teachers[0]
        self.client.login(username=teacher.username, password='password')
        response = self.client.get('/teach/%s/moderate' % self.program.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertIn('prog', response.context)

    def test_moderate_post_create_record(self):
        """Test submitting the moderator signup form for a new record."""
        teacher = self.teachers[0]
        self.client.login(username=teacher.username, password='password')
        post_data = {
            'will_moderate': 'True',
            'num_slots': '1',
            'class_categories': [cat.id for cat in self.categories],
            'comments': 'Test comment'
        }
        response = self.client.post('/teach/%s/moderate' % self.program.url, post_data)
        
        # Should redirect to core (302)
        self.assertEqual(response.status_code, 302)
        
        record = ModeratorRecord.objects.get(user=teacher, program=self.program)
        self.assertTrue(record.will_moderate)
        self.assertEqual(record.num_slots, 1)
        self.assertEqual(record.comments, 'Test comment')
        self.assertEqual(record.class_categories.count(), len(self.categories))

    def test_moderate_post_invalid(self):
        """Test form submission with missing required data."""
        teacher = self.teachers[0]
        self.client.login(username=teacher.username, password='password')
        post_data = {'will_moderate': 'True'} # missing num_slots
        response = self.client.post('/teach/%s/moderate' % self.program.url, post_data)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertTrue(response.context['form'].errors)

    def test_teachers_queryset(self):
        """Test that the teachers() helper returns the correct querysets for offered and assigned moderators."""
        teacher = self.teachers[0]
        # Initially empty
        res = self.moduleobj.teachers()
        self.assertEqual(res['will_moderate'].count(), 0)
        self.assertEqual(res['assigned_moderator'].count(), 0)
        
        # 1. Test offered_list (will_moderate)
        ModeratorRecord.objects.create(user=teacher, program=self.program, will_moderate=True, num_slots=1)
        res = self.moduleobj.teachers()
        self.assertEqual(res['will_moderate'].count(), 1)
        self.assertEqual(res['will_moderate'][0], teacher)
        
        # 2. Test assigned_list (assigned_moderator)
        # Assign the teacher as a moderator to a section in this program
        section = ClassSection.objects.filter(parent_class__parent_program=self.program)[0]
        section.moderator = teacher
        section.save()
        
        res = self.moduleobj.teachers()
        self.assertEqual(res['assigned_moderator'].count(), 1)
        self.assertEqual(res['assigned_moderator'][0], teacher)

    def test_teacher_desc(self):
        """Test that teacher descriptions correctly use the moderator_title tag if present."""
        desc = self.moduleobj.teacherDesc()
        self.assertIn("moderator", desc['will_moderate'].lower())
        
        # Test with custom tag
        Tag.objects.create(tag="moderator_title", program=self.program, content="Helper")
        desc = self.moduleobj.teacherDesc()
        self.assertIn("helper", desc['will_moderate'].lower())

    def test_moderator_lookup_logic(self):
        """Test the moderator lookup AJAX logic for searching teachers by name."""
        teacher = self.teachers[0]
        ModeratorRecord.objects.create(user=teacher, program=self.program, will_moderate=True, num_slots=1)
        
        factory = RequestFactory()
        request = factory.get('/fake', {'name': teacher.last_name})
        
        # Mock prog object
        mock_prog = MagicMock()
        mock_prog.teachers.return_value = self.moduleobj.teachers()
        
        response = TeacherModeratorModule.moderatorlookup_logic(request, None, None, None, None, None, mock_prog)
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content.decode('utf-8'))
        self.assertTrue(any(item['id'] == teacher.id for item in data))
        self.assertEqual(data[0]['username'], teacher.username)

    def test_is_step(self):
        """Verify isStep is False."""
        self.assertFalse(self.moduleobj.isStep())
