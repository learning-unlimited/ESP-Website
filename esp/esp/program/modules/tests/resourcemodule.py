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
from esp.resources.models import Resource, ResourceType

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

    def _create_import_resources(self):
        """Create two source classrooms and two floating resources, each
        with a distinct resource type, in a past program."""
        self.create_past_program()
        past_program = self.new_prog
        past_timeslot = past_program.getTimeSlots().first()

        classroom_type = ResourceType.get_or_create('Classroom')
        selected_room = Resource.objects.create(
            name='Past A', res_type=classroom_type, num_students=20,
            event=past_timeslot)
        unselected_room = Resource.objects.create(
            name='Past B', res_type=classroom_type, num_students=20,
            event=past_timeslot)

        projector_type = ResourceType.objects.create(
            name='Projector', description='Projector', program=past_program)
        whiteboard_type = ResourceType.objects.create(
            name='Whiteboard', description='Whiteboard', program=past_program)
        Resource.objects.create(
            name='Projector', res_type=projector_type, event=past_timeslot,
            res_group=selected_room.res_group)
        Resource.objects.create(
            name='Whiteboard', res_type=whiteboard_type, event=past_timeslot,
            res_group=unselected_room.res_group)

        laptop_type = ResourceType.objects.create(
            name='Laptop', description='Laptop', program=past_program)
        camera_type = ResourceType.objects.create(
            name='Camera', description='Camera', program=past_program)
        selected_equipment = Resource.objects.create(
            name='Laptop cart', res_type=laptop_type, event=past_timeslot)
        Resource.objects.create(
            name='Camera kit', res_type=camera_type, event=past_timeslot)
        return (past_program, selected_room, unselected_room,
                selected_equipment)

    def _resource_import_url(self, kind):
        return '/manage/%s/resources/%s_import' % (
            self.program.getUrlBase(), kind)

    def test_classroom_import_creates_types_only_for_selected_rooms(self):
        """Furnishing types for unchecked classrooms are not imported."""
        (past_program, selected_room, _, _) = \
            self._create_import_resources()
        post_data = {
            'program': str(past_program.id),
            'complete_availability': 'on',
            'import_furnishings': 'on',
            'import_confirm': 'yes',
            'to_import': [str(selected_room.id)],
        }

        response = self.client.post(
            self._resource_import_url('classroom'), post_data)

        self.assertEqual(response.status_code, 200)
        imported_types = set(ResourceType.objects.filter(
            program=self.program).values_list('name', flat=True))
        self.assertIn('Projector', imported_types)
        self.assertNotIn('Whiteboard', imported_types)
        self.assertTrue(Resource.objects.filter(
            event__program=self.program, name='Past A',
            res_type__name='Classroom').exists())
        self.assertFalse(Resource.objects.filter(
            event__program=self.program, name='Past B',
            res_type__name='Classroom').exists())
        self.assertFalse(Resource.objects.filter(
            event__program=self.program, res_type__name='Whiteboard').exists())
        self.assertEqual(Resource.objects.filter(
            event__program=self.program, res_type__name='Projector').count(),
            self.program.getTimeSlots().count())

        # A retry should not duplicate the selected room or furnishing type.
        self.client.post(self._resource_import_url('classroom'), post_data)
        self.assertEqual(ResourceType.objects.filter(
            program=self.program, name='Projector').count(), 1)
        self.assertEqual(Resource.objects.filter(
            event__program=self.program, name='Past A',
            res_type__name='Classroom').count(),
            self.program.getTimeSlots().count())

    def test_complete_equipment_import_creates_types_only_for_selected_items(self):
        """Complete-availability imports do not create unchecked equipment types."""
        (past_program, _, _, selected_equipment) = \
            self._create_import_resources()
        post_data = {
            'program': str(past_program.id),
            'complete_availability': 'on',
            'import_confirm': 'yes',
            'to_import': [str(selected_equipment.id)],
        }

        response = self.client.post(
            self._resource_import_url('equipment'), post_data)

        self.assertEqual(response.status_code, 200)
        imported_types = set(ResourceType.objects.filter(
            program=self.program).values_list('name', flat=True))
        self.assertIn('Laptop', imported_types)
        self.assertNotIn('Camera', imported_types)
        self.assertTrue(Resource.objects.filter(
            event__program=self.program, name='Laptop cart').exists())
        self.assertFalse(Resource.objects.filter(
            event__program=self.program, name='Camera kit').exists())

        # A retry should not duplicate the resource type or per-timeslot items.
        self.client.post(self._resource_import_url('equipment'), post_data)
        self.assertEqual(ResourceType.objects.filter(
            program=self.program, name='Laptop').count(), 1)
        self.assertEqual(Resource.objects.filter(
            event__program=self.program, name='Laptop cart').count(),
            self.program.getTimeSlots().count())

    def _timeslot_url(self):
        return '/manage/%s/resources/timeslot' % self.program.getUrlBase()

    def _timeslot_data(self, name, start, **overrides):
        data = {
            'command': 'addedit',
            'id': '',
            'name': name,
            'description': 'desc',
            'start': start,
            'hours': '1',
            'minutes': '0',
            'group': '',
        }
        data.update(overrides)
        return data

    def testTimeslotDuplicateRejected(self):
        """Submitting an identical timeslot twice is rejected with a form error."""
        data = self._timeslot_data('Duplicate Test Slot', '10/14/2027 09:00:00')

        response = self.client.post(self._timeslot_url(), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Event.objects.filter(
            program=self.program, short_description='Duplicate Test Slot').count(), 1)

        response = self.client.post(self._timeslot_url(), data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('already exists', response.content.decode('UTF-8'))
        self.assertEqual(Event.objects.filter(
            program=self.program, short_description='Duplicate Test Slot').count(), 1)

    def testTimeslotDuplicateAllowsOtherType(self):
        """A timeslot of a different type at the same times is not a duplicate."""
        self.client.post(self._timeslot_url(),
                         self._timeslot_data('Regular Slot', '10/16/2027 09:00:00'))
        response = self.client.post(self._timeslot_url(),
                                    self._timeslot_data('Open Slot', '10/16/2027 09:00:00', openclass='on'))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('already exists', response.content.decode('UTF-8'))
        self.assertTrue(Event.objects.filter(
            program=self.program, short_description='Open Slot').exists())

    def testTimeslotEditWithoutChangeDoesNotSelfFlag(self):
        """Re-saving an existing timeslot unchanged is not flagged as a duplicate of itself."""
        data = self._timeslot_data('Edit Test Slot', '10/15/2027 09:00:00')
        self.client.post(self._timeslot_url(), data)
        created = Event.objects.get(program=self.program, short_description='Edit Test Slot')

        response = self.client.post(self._timeslot_url(), dict(data, id=str(created.id)))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('already exists', response.content.decode('UTF-8'))
        self.assertEqual(Event.objects.filter(
            program=self.program, short_description='Edit Test Slot').count(), 1)

    def testTimeslotEditIntoDuplicateRejected(self):
        """Editing a timeslot so it matches another existing timeslot is rejected."""
        self.client.post(self._timeslot_url(),
                         self._timeslot_data('Slot A', '10/17/2027 09:00:00'))
        self.client.post(self._timeslot_url(),
                         self._timeslot_data('Slot B', '10/17/2027 11:00:00'))
        slot_b = Event.objects.get(program=self.program, short_description='Slot B')

        response = self.client.post(self._timeslot_url(), self._timeslot_data(
            'Slot B', '10/17/2027 09:00:00', id=str(slot_b.id)))
        self.assertEqual(response.status_code, 200)
        self.assertIn('already exists', response.content.decode('UTF-8'))
        slot_b.refresh_from_db()
        self.assertEqual(slot_b.start.hour, 11)
