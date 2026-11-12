from esp.program.models import ClassSection
from esp.program.tests import ProgramFrameworkTest
from esp.resources.models import Resource


class AssignStartTimeRoomTest(ProgramFrameworkTest):
    """ClassSection.assign_start_time should keep the section's room when the
    room is free at the new time, and quietly drop it otherwise."""

    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_timeslots': 3,
            'num_rooms': 2,
            'num_teachers': 2,
            'classes_per_teacher': 1,
            'sections_per_class': 1,
        })
        super().setUp(*args, **kwargs)
        self.section = ClassSection.objects.filter(parent_class__parent_program=self.program).first()
        self.ts = list(self.timeslots)
        self.section.clearRooms()
        self.section.clear_meeting_times()
        self.section.assign_meeting_times([self.ts[0]])
        self.room_name = 'Room 0'
        status, _ = self.section.assign_room(self._room(self.ts[0]))
        self.assertTrue(status)

    def _room(self, timeslot):
        return Resource.objects.get(name=self.room_name, event=timeslot)

    def _classroom_slots(self):
        return list(self.section.classrooms().values_list('name', 'event_id'))

    def test_room_kept_when_free_at_new_time(self):
        self.section.assign_start_time(self.ts[1])
        self.assertEqual(self._classroom_slots(), [(self.room_name, self.ts[1].id)])

    def test_room_dropped_when_taken_at_new_time(self):
        other = ClassSection.objects.filter(parent_class__parent_program=self.program).exclude(id=self.section.id).first()
        other.clearRooms()
        other.clear_meeting_times()
        other.assign_meeting_times([self.ts[1]])
        other.assign_room(self._room(self.ts[1]))

        self.section.assign_start_time(self.ts[1])
        self.assertEqual(self._classroom_slots(), [])
        self.assertEqual(list(self.section.meeting_times.all()), [self.ts[1]])
        self.assertEqual(list(other.classrooms().values_list('name', flat=True)), [self.room_name])

    def test_room_dropped_without_error_when_room_missing_at_new_time(self):
        self._room(self.ts[1]).delete()
        self.section.assign_start_time(self.ts[1])
        self.assertEqual(self._classroom_slots(), [])
        self.assertEqual(list(self.section.meeting_times.all()), [self.ts[1]])


class ResourceIsAvailableTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        kwargs.update({'num_timeslots': 2, 'num_rooms': 1, 'num_teachers': 1,
                       'classes_per_teacher': 1, 'sections_per_class': 1})
        super().setUp(*args, **kwargs)

    def test_timeslot_argument(self):
        ts0, ts1 = list(self.timeslots)
        room = Resource.objects.get(name='Room 0', event=ts0)
        self.assertTrue(room.is_available(timeslot=ts1))

    def test_timeslot_argument_missing_resource(self):
        ts0, ts1 = list(self.timeslots)
        room = Resource.objects.get(name='Room 0', event=ts0)
        Resource.objects.get(name='Room 0', event=ts1).delete()
        self.assertFalse(room.is_available(timeslot=ts1))
