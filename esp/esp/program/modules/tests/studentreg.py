__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2011 by the individual contributors
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
  Email: web-team@lists.learningu.org
"""

from esp.program.modules.base import ProgramModuleObj
from esp.program.tests import ProgramFrameworkTest

import random
import re

class StudentRegTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        from esp.program.modules.base import ProgramModule, ProgramModuleObj
        
        # Set up the program -- we want to be sure of these parameters
        kwargs.update( {
            'num_timeslots': 3, 'timeslot_length': 50, 'timeslot_gap': 10,
            'num_teachers': 6, 'classes_per_teacher': 1, 'sections_per_class': 2,
            'num_rooms': 6,
            } )
        super(StudentRegTest, self).setUp(*args, **kwargs)
        
        self.add_student_profiles()
        self.schedule_randomly()

        #   Make all modules non-required for now, so we don't have to be shown required pages
        for pmo in self.program.getModules():
            pmo.__class__ = ProgramModuleObj
            pmo.required = False
            pmo.save()

        # Get and remember the instance of StudentClassRegModule
        pm = ProgramModule.objects.get(handler='StudentClassRegModule')
        self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, pm)
        self.moduleobj.user = self.students[0]

    def test_confirm(self):
        program = self.program

        #   Pick a student and log in
        student = random.choice(self.students)
        self.failUnless( self.client.login( username=student.username, password='password' ), "Couldn't log in as student %s" % student.username )

        #   Sign up for a class directly
        sec = random.choice(program.sections())
        sec.preregister_student(student)

        #   Get the receipt and check that the class appears on it with title and time
        response = self.client.get('/learn/%s/confirmreg' % self.program.getUrlBase())
        self.assertTrue(sec.title() in response.content)
        for ts in sec.meeting_times.all():
            self.assertTrue(ts.short_description in response.content)

    def test_catalog(self):

        def verify_catalog_correctness():
            response = self.client.get('/learn/%s/catalog' % program.getUrlBase())
            for cls in self.program.classes():
                #   Find the portion of the catalog corresponding to this class
                pattern = r"""<div class="show_class">\s*<table [^>]+ >\s*<tr onclick="swap_visible\('class_%d_details'\).*?</table>\s*</div>""" % cls.id
                cls_fragment = re.search(pattern, response.content, re.DOTALL).group(0)

                pat2 = r"""<th [^>]+>\s*(?P<title>.*?)\s*<br />.*?<td colspan="3" class="info">(?P<description>.*?)</td>.*?<strong>Enrollment</strong>(?P<enrollment>.*?)</td>"""
                cls_info = re.search(pat2, cls_fragment, re.DOTALL).groupdict(0) 
                
                #   Check title
                title = cls_info['title'].strip()
                expected_title = '%s: %s' % (cls.emailcode(), cls.title())
                self.assertTrue(title == expected_title, 'Incorrect class title in catalog: got %s, expected %s' % (title, expected_title))

                #   Check description
                description = cls_info['description'].replace('<br />', '').strip()
                self.assertTrue(description == cls.class_info.strip(), 'Incorrect class description in catalog: got %s, expected %s' % (description, cls.class_info.strip()))

                #   Check enrollments
                enrollments = [x.replace('<br />', '').strip() for x in cls_info['enrollment'].split('Section')[1:]]
                for sec in cls.sections.order_by('id'):
                    i = sec.index() - 1
                    expected_str = '%s: %s (max %s)' % (sec.index(), sec.num_students(), sec.capacity)
                    self.assertTrue(enrollments[i] == expected_str, 'Incorrect enrollment for %s in catalog: got %s, expected %s' % (sec.emailcode(), enrollments[i], expected_str))

        program = self.program

        #   Get the catalog and check that everything is OK
        verify_catalog_correctness()

        #   Change a class title and check
        cls = random.choice(program.classes())
        a = cls.anchor
        a.friendly_name = 'New %s' % cls.title()
        a.save()
        verify_catalog_correctness()

        #   Change a class description and check
        cls2 = random.choice(program.classes())
        cls2.class_info = 'New %s' % cls2.class_info
        cls2.save()
        verify_catalog_correctness()

        #   Register a student for a class and check    
        sec = random.choice(program.sections())
        student = random.choice(self.students)
        sec.preregister_student(student)
        verify_catalog_correctness()

    def test_profile(self):
        def template_names(response):
            return [x.name for x in response.template]        

        def expect_template(response, template):
            self.assertTrue(template in template_names(response), 'Wrong template for profile: got %s, expected %s' % (template_names(response), template))

        #   Login as a student and ensure we can submit the profile
        student = random.choice(self.students)
        self.failUnless( self.client.login( username=student.username, password='password' ), "Couldn't log in as student %s" % student.username )
        response = self.client.get('/learn/%s/profile' % self.program.getUrlBase())
        expect_template(response, 'users/profile.html')      

        #   Login as a teacher and ensure we get the right message
        teacher = random.choice(self.teachers)
        self.failUnless( self.client.login( username=teacher.username, password='password' ), "Couldn't log in as student %s" % teacher.username )
        response = self.client.get('/learn/%s/profile' % self.program.getUrlBase())
        expect_template(response, 'errors/program/notastudent.html')

        #   Login as an admin and ensure we get the right message
        admin = random.choice(self.admins)
        self.failUnless( self.client.login( username=admin.username, password='password' ), "Couldn't log in as student %s" % admin.username )
        response = self.client.get('/learn/%s/profile' % self.program.getUrlBase())
        expect_template(response, 'users/profile.html')


