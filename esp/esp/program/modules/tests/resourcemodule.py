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
from esp.cal.models import Event
from django.db import IntegrityError, transaction

import re

class ResourceModuleTest(ProgramFrameworkTest):
    ## This test is very incomplete.
    ## It needs more data, more interesting state in the program in question.
    ## It also needs all of the queries in self.program.students() and
    ## self.program.teachers() to have their own tests for correctness;
    ## at the moment it just assumes that they are correct.
    ## It also also needs to test all the other queries on this page.

    def setUp(self):
        super().setUp()

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
        results = re.findall(regexp, str(response.content, encoding='UTF-8'))
        displayed_names = {x[index] for x in results}

        return displayed_names

    def checkDisplayedClassroomList(self):
        #   Compute the list of classroom names for the program
        program_classroom_names = {str(x.name) for x in self.program.groupedClassrooms()}

        #   Compare to those shown on the resources page
        self.assertEqual(program_classroom_names, self.getDisplayedList(r'<div id="classroom-([0-9]+)">(.*?)</div>', 1))

        return program_classroom_names

    def checkDisplayedResourceTypeList(self):
        #   Compute the list of resource type names for the program
        program_restype_names = {str(x.name) for x in self.program.getResourceTypes()}

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
        matching_rooms = [x for x in self.program.groupedClassrooms() if x.name == 'New Room']
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

    def _assert_bad_request(self, url, params):
        response = self.client.get(url, params)
        self.assertEqual(response.status_code, 400)

    def _assert_post_bad_request(self, url, data):
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 400)

    def testStaleOrInvalidIds(self):
        base = '/manage/%s/resources' % self.program.getUrlBase()
        nonexistent_id = '999999999'
        invalid_id = 'not-an-int'

        for section in ('timeslot', 'restype', 'classroom', 'equipment'):
            section_url = '%s/%s' % (base, section)

            for op in ('edit', 'delete'):
                # missing id
                self._assert_bad_request(section_url, {'op': op})
                # non-integer id
                self._assert_bad_request(section_url, {'op': op, 'id': invalid_id})
                # nonexistent (stale) id
                self._assert_bad_request(section_url, {'op': op, 'id': nonexistent_id})

    def testStaleOrInvalidPostIds(self):
        base = '/manage/%s/resources' % self.program.getUrlBase()
        nonexistent_id = '999999999'
        invalid_id = 'not-an-int'

        for section in ('timeslot', 'restype', 'classroom', 'equipment'):
            section_url = '%s/%s' % (base, section)
            for bad_id in (nonexistent_id, invalid_id):
                # reallyremove with tampered/stale id
                self._assert_post_bad_request(section_url, {
                    'command': 'reallyremove',
                    'id': bad_id,
                })
                # addedit with tampered/stale id
                self._assert_post_bad_request(section_url, {
                    'command': 'addedit',
                    'id': bad_id,
                })
            # reallyremove with missing id entirely
            self._assert_post_bad_request(section_url, {
                'command': 'reallyremove',
            })

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
        matching_restypes = [x for x in self.program.getResourceTypes() if x.name == 'New Resource Type']
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

    def testTimeslotDuplicateRejected(self):
        """Duplicate timeslot creation via manual add is rejected with a form error."""
        timeslot_url = '/manage/%s/resources/timeslot' % self.program.getUrlBase()

        add_timeslot_data = {
            'command': 'addedit',
            'id': '',
            'name': 'Duplicate Test Slot',
            'description': 'desc',
            'start': '10/14/2027 09:00:00',
            'hours': '1',
            'minutes': '0',
            'openclass': False,
            'compulsory': False,
            'group': '',
        }

        before_count = Event.objects.filter(
            program=self.program, short_description='Duplicate Test Slot'
        ).count()

        # First submission should succeed
        response = self.client.post(timeslot_url, add_timeslot_data)
        self.assertEqual(response.status_code, 200)

        after_first_count = Event.objects.filter(
            program=self.program, short_description='Duplicate Test Slot'
        ).count()
        self.assertEqual(after_first_count, before_count + 1)

        # Second, identical submission should be rejected — event count must not increase
        response = self.client.post(timeslot_url, add_timeslot_data)
        self.assertEqual(response.status_code, 200)  # re-renders form with errors, not a 4xx
        self.assertIn('already exists', str(response.content, encoding='UTF-8'))

        after_second_count = Event.objects.filter(
            program=self.program, short_description='Duplicate Test Slot'
        ).count()
        self.assertEqual(
            after_second_count, after_first_count,
            "Duplicate timeslot was persisted despite validation"
        )

    def testTimeslotEditWithoutChangeDoesNotSelfFlag(self):
        """Editing an existing timeslot without changing start/end should not be
        falsely rejected as a duplicate of itself."""
        timeslot_url = '/manage/%s/resources/timeslot' % self.program.getUrlBase()

        add_timeslot_data = {
            'command': 'addedit',
            'id': '',
            'name': 'Edit Test Slot',
            'description': 'desc',
            'start': '10/15/2027 09:00:00',
            'hours': '1',
            'minutes': '0',
            'openclass': False,
            'compulsory': False,
            'group': '',
        }
        response = self.client.post(timeslot_url, add_timeslot_data)
        self.assertEqual(response.status_code, 200)

        created = Event.objects.get(program=self.program, short_description='Edit Test Slot')

        # Resubmit with the same id and same start/end — should succeed, not self-flag
        edit_data = dict(add_timeslot_data)
        edit_data['id'] = str(created.id)

        response = self.client.post(timeslot_url, edit_data)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('already exists', str(response.content, encoding='UTF-8'))

        # Still exactly one matching event — not duplicated, not rejected
        matching_count = Event.objects.filter(
            program=self.program, short_description='Edit Test Slot'
        ).count()
        self.assertEqual(matching_count, 1)

    def testTimeslotUniqueConstraintHoldsAtDbLevel(self):
        """The DB-level UniqueConstraint on Event(program, start, end) holds even
        when the form/validation layer is bypassed entirely."""
        existing_type = self.program.getTimeSlots().first().event_type
        start = self.program.getTimeSlots().first().start

        from datetime import timedelta
        end = start + timedelta(hours=1)

        Event.objects.create(
            program=self.program, start=start, end=end,
            description='RaceTest', short_description='RaceTest',
            event_type=existing_type,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Event.objects.create(
                    program=self.program, start=start, end=end,
                    description='RaceTest2', short_description='RaceTest2',
                    event_type=existing_type,
                )