__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2012 by the individual contributors
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
from esp.program.modules.base import ProgramModule, ProgramModuleObj

import re

class ResourceModuleTest(ProgramFrameworkTest):
    ## This test is very incomplete.
    ## It needs more data, more interesting state in the program in question.
    ## It also needs all of the queries in self.program.students() and
    ## self.program.teachers() to have their own tests for correctness;
    ## at the moment it just assumes that they are correct.
    ## It also also needs to test all the other queries on this page.

    def setUp(self):
        super(ResourceModuleTest, self).setUp()

        if not getattr(self, 'isSetUp', False):
            self.pm = ProgramModule.objects.get(handler='ResourceModule')
            self.moduleobj = ProgramModuleObj.getFromProgModule(self.program, self.pm)
            self.moduleobj.user = self.admins[0]

            self.client.login(username=self.admins[0].username, password='password')
            self.response = self.client.get('/manage/%s/dashboard' % self.program.getUrlBase())

            self.isSetUp = True  ## Save duplicate sets of queries on setUp

    def getDisplayedList(self, regexp, index):
        #   Fetch the resource management page
        response = self.client.get('/manage/%s/resources' % self.program.getUrlBase())
        self.assertEqual(response.status_code, 200)

        #   Search for matching items in the response and ensure they are consistent
        results = re.findall(regexp, response.content)
        displayed_names = set([x[index] for x in results])

        return displayed_names

    def checkDisplayedClassroomList(self):
        #   Compute the list of classroom names for the program
        program_classroom_names = set([str(x.name) for x in self.program.groupedClassrooms()])

        #   Compare to those shown on the resources page
        self.assertEqual(program_classroom_names, self.getDisplayedList(r'<div id="classroom-([0-9]+)">(.*?)</div>', 1))

        return program_classroom_names

    def checkDisplayedResourceTypeList(self):
        #   Compute the list of resource type names for the program
        program_restype_names = set([str(x.name) for x in self.program.getResourceTypes()])

        #   Compare to those shown on the resources page
        self.assertEqual(program_restype_names, self.getDisplayedList(r'<div id="restype-([0-9]+)">(.*?)</div>', 1))

        return program_restype_names

    def testClassrooms(self):
        #   Check that the list of classrooms on the resource management page matches those known for the program
        self.checkDisplayedClassroomList()

        #   Check that we can add a classroom and have it show up
        add_classroom_data = {
            'command': 'addedit',
            'room_number': 'New Room',
            'times_available': tuple(self.program.getTimeSlots().values_list('id', flat=True)),
            'num_students': '11',
            'id': '',
            'orig_room_number': '',
        }
        response = self.client.post('/manage/%s/resources/classroom' % self.program.getUrlBase(), add_classroom_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('New Room', self.checkDisplayedClassroomList())   #   checks consistency and presence of new room

        #   Check that we can edit a classroom and have it show up
        matching_rooms = filter(lambda x: x.name == 'New Room', self.program.groupedClassrooms())
        self.assertEqual(len(matching_rooms), 1)
        target_room = matching_rooms[0]
        edit_classroom_data = {
            'command': 'addedit',
            'room_number': 'Edited Room',
            'times_available': tuple(self.program.getTimeSlots().values_list('id', flat=True)),
            'num_students': '11',
            'id': str(target_room.id),
            'orig_room_number': 'New Room',
        }
        response = self.client.post('/manage/%s/resources/classroom' % self.program.getUrlBase(), edit_classroom_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Edited Room', self.checkDisplayedClassroomList())   #   checks consistency and presence of edited room

        #   Check that we can delete a classroom and have it disappear
        delete_classroom_data = {
            'command': 'reallyremove',
            'id': str(target_room.id),
        }
        response = self.client.post('/manage/%s/resources/classroom' % self.program.getUrlBase(), delete_classroom_data)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Edited Room', self.checkDisplayedClassroomList())   #   checks consistency and presence of room

    def testResourceTypes(self):
        #   Check that resource types started out consistent
        self.checkDisplayedResourceTypeList()

        #   Check that we can add a resource type and have it show up
        add_restype_data = {
            'command': 'addedit',
            'name': 'New Resource Type',
            'description': "Test description",
            'priority': '1',
            'id': '',
        }
        response = self.client.post('/manage/%s/resources/restype' % self.program.getUrlBase(), add_restype_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('New Resource Type', self.checkDisplayedResourceTypeList())

        #   ... even if the priority is not specified
        add_restype_data = {
            'command': 'addedit',
            'name': 'New Resource Type 2',
            'description': "Test description",
            'priority': '',
            'id': '',
        }
        response = self.client.post('/manage/%s/resources/restype' % self.program.getUrlBase(), add_restype_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('New Resource Type 2', self.checkDisplayedResourceTypeList())

        #   Check that we can edit a resource type and have it show up
        matching_restypes = filter(lambda x: x.name == 'New Resource Type', self.program.getResourceTypes())
        self.assertEqual(len(matching_restypes), 1)
        target_restype = matching_restypes[0]
        edit_restype_data = {
            'command': 'addedit',
            'name': 'Edited Resource Type',
            'description': "Test description",
            'priority': '1',
            'id': str(target_restype.id),
        }
        response = self.client.post('/manage/%s/resources/restype' % self.program.getUrlBase(), edit_restype_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Edited Resource Type', self.checkDisplayedResourceTypeList())

        #   Check that we can delete a resource type and have it disappear
        delete_restype_data = {
            'command': 'reallyremove',
            'id': str(target_restype.id),
        }
        response = self.client.post('/manage/%s/resources/restype' % self.program.getUrlBase(), delete_restype_data)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Edited Resource Type', self.checkDisplayedResourceTypeList())


