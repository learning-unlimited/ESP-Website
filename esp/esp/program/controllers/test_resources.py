"""
Unit tests for esp/esp/program/controllers/resources.py

Tests for the ResourceController class, which handles CRUD operations
for program timeslots, resource types, classrooms, and equipment.

Uses ProgramFrameworkTest as the base — gives us a program with
timeslots, rooms, teachers, and students out of the box.
"""

from unittest.mock import Mock

from esp.cal.models import Event
from esp.middleware import ESPError
from esp.program.controllers.resources import ResourceController
from esp.program.models import ClassSection
from esp.resources.models import ResourceType, Resource
from esp.program.tests import ProgramFrameworkTest


class ResourceControllerInitTest(ProgramFrameworkTest):
    def test_program_is_stored(self):
        ctrl = ResourceController(self.program)
        self.assertEqual(ctrl.program, self.program)


class TimeslotTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.ctrl = ResourceController(self.program)

    def test_delete_timeslot(self):
        slot = self.timeslots.first()
        self.ctrl.delete_timeslot(slot.id)
        self.assertFalse(Event.objects.filter(id=slot.id).exists())

    def test_delete_timeslot_bad_id(self):
        with self.assertRaises(Event.DoesNotExist):
            self.ctrl.delete_timeslot(999999)

    def test_add_new_timeslot(self):
        form = Mock()
        form.cleaned_data = {'id': None}
        result = self.ctrl.add_or_edit_timeslot(form)
        self.assertIsInstance(result, Event)
        form.save_timeslot.assert_called_once_with(self.program, result)

    def test_edit_timeslot(self):
        existing = self.timeslots.first()
        form = Mock()
        form.cleaned_data = {'id': existing.id}
        result = self.ctrl.add_or_edit_timeslot(form)
        self.assertEqual(result.id, existing.id)
        form.save_timeslot.assert_called_once()


class ResTypeTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.ctrl = ResourceController(self.program)

    def test_delete_restype(self):
        rt = ResourceType.objects.create(
            name='Projector', description='test', program=self.program)
        self.ctrl.delete_restype(rt.id)
        self.assertFalse(ResourceType.objects.filter(id=rt.id).exists())

    def test_delete_restype_bad_id(self):
        with self.assertRaises(ResourceType.DoesNotExist):
            self.ctrl.delete_restype(999999)

    def test_add_new_restype(self):
        form = Mock()
        form.cleaned_data = {'id': None}
        result = self.ctrl.add_or_edit_restype(form)
        self.assertIsInstance(result, ResourceType)
        form.save_restype.assert_called_once_with(self.program, result, None)

    def test_add_restype_with_choices(self):
        form = Mock()
        form.cleaned_data = {'id': None}
        choices = ['Whiteboard', 'Chalkboard']
        self.ctrl.add_or_edit_restype(form, choices=choices)
        form.save_restype.assert_called_once()
        # make sure choices got passed through
        args = form.save_restype.call_args[0]
        self.assertEqual(args[2], choices)

    def test_edit_existing_restype(self):
        rt = ResourceType.objects.create(
            name='Whiteboard', description='', program=self.program)
        form = Mock()
        form.cleaned_data = {'id': rt.id}
        result = self.ctrl.add_or_edit_restype(form)
        self.assertEqual(result.id, rt.id)


class DeleteClassroomTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.schedule_randomly()
        self.ctrl = ResourceController(self.program)

    def test_delete_classroom_removes_room(self):
        room = self.rooms.first()
        name = room.name
        self.ctrl.delete_classroom(room.id)
        self.assertFalse(
            self.program.getClassrooms().filter(name=name).exists())

    def test_delete_classroom_clears_sections(self):
        """Sections in the room should get their schedule wiped."""
        scheduled = ClassSection.objects.filter(
            resourceassignment__resource__in=self.rooms,
            parent_class__parent_program=self.program,
        ).distinct()
        if not scheduled.exists():
            return  # nothing scheduled, skip
        section = scheduled.first()
        room = section.resourceassignment_set.first().resource
        self.ctrl.delete_classroom(room.id)
        section.refresh_from_db()
        self.assertEqual(section.meeting_times.count(), 0)

    def test_delete_classroom_bad_id(self):
        with self.assertRaises(Resource.DoesNotExist):
            self.ctrl.delete_classroom(999999)


class AddClassroomTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.ctrl = ResourceController(self.program)

    def test_save_with_furnishings(self):
        form = Mock()
        furnishings = [{'furnishing': '1', 'choice': ''}]
        self.ctrl.add_or_edit_classroom(form, furnishings=furnishings)
        form.save_classroom.assert_called_once_with(
            self.program, furnishings=furnishings)

    def test_save_no_furnishings(self):
        form = Mock()
        self.ctrl.add_or_edit_classroom(form)
        form.save_classroom.assert_called_once_with(
            self.program, furnishings=None)


class DeleteEquipmentTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.ctrl = ResourceController(self.program)
        # set up a piece of equipment across all timeslots
        self.equip_type = ResourceType.objects.create(
            name='Speaker', description='portable', program=self.program)
        self.equip_ids = []
        for slot in self.timeslots:
            r = Resource.objects.create(
                name='Speaker-1', res_type=self.equip_type,
                event=slot, is_unique=True)
            self.equip_ids.append(r.id)

    def test_delete_equipment_all_slots(self):
        self.ctrl.delete_equipment(self.equip_ids[0])
        remaining = Resource.objects.filter(id__in=self.equip_ids).count()
        self.assertEqual(remaining, 0)

    def test_delete_equipment_bad_id(self):
        with self.assertRaises(Resource.DoesNotExist):
            self.ctrl.delete_equipment(999999)
