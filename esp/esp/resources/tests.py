from datetime import datetime, timedelta

from django.db.models import ProtectedError

from esp.cal.models import Event, EventType
from esp.program.models import Program
from esp.program.models.class_ import ClassSubject, ClassSection, ClassCategories
from esp.resources.models import Resource, ResourceType, ResourceRequest, ResourceAssignment
from esp.tests.util import CacheFlushTestCase as TestCase

class ResourceTypeTest(TestCase):

    def setUp(self):
        super().setUp()
        now = datetime.now()
        self.event = Event.objects.create(
            name='event', start=now, end=now,
            short_description='', description='',
            event_type=EventType.objects.all()[0],
        )
        self.program = Program.objects.create(grade_min=7, grade_max=12)
        self.subject = ClassSubject.objects.create(
            category=ClassCategories.objects.all()[0],
            grade_min=7, grade_max=12,
            parent_program=self.program,
            class_size_max=30,
            class_info='class',
        )
        self.section = ClassSection.objects.create(parent_class=self.subject)

    def testCascadingDeleteDisabled(self):
        res_type = ResourceType.objects.create(name='res_type', description='')

        resource = Resource.objects.create(name='resource', res_type=res_type, event=self.event)
        with self.assertRaises(ProtectedError):
            res_type.delete()
        resource.delete()

        resource_request = ResourceRequest.objects.create(desired_value='desired_value', res_type=res_type, target=self.section)
        with self.assertRaises(ProtectedError):
            res_type.delete()
        resource_request.delete()

        # This should now be okay.
        res_type.delete()

class FloatingResourceAvailabilityTest(TestCase):

    def setUp(self):
        super(FloatingResourceAvailabilityTest, self).setUp()
        now = datetime.now().replace(minute=0, second=0, microsecond=0)
        event_type = EventType.objects.all()[0]
        self.program = Program.objects.create(grade_min=7, grade_max=12)

        # Create two consecutive timeslots
        self.timeslot1 = Event.objects.create(
            name='Slot 1', start=now, end=now + timedelta(hours=1),
            short_description='', description='',
            event_type=event_type, program=self.program,
        )
        self.timeslot2 = Event.objects.create(
            name='Slot 2', start=now + timedelta(hours=1), end=now + timedelta(hours=2),
            short_description='', description='',
            event_type=event_type, program=self.program,
        )

        self.res_type = ResourceType.objects.create(name='Projector', description='')
        self.subject = ClassSubject.objects.create(
            category=ClassCategories.objects.all()[0],
            grade_min=7, grade_max=12,
            parent_program=self.program,
            class_size_max=30,
            class_info='class',
        )
        self.section = ClassSection.objects.create(parent_class=self.subject)

        # Create floating resource copies for each timeslot
        self.res_ts1 = Resource.objects.create(
            name='Projector #1', res_type=self.res_type, event=self.timeslot1,
        )
        self.res_ts2 = Resource.objects.create(
            name='Projector #1', res_type=self.res_type, event=self.timeslot2,
        )

    def test_available_when_no_prior_assignment(self):
        """Resource is available when it has no assignment in any timeslot."""
        available = self.program.getAvailableResources(self.timeslot2)
        available_names = [r.name for r in available]
        self.assertIn('Projector #1', available_names)

    def test_available_when_prior_assignment_returned(self):
        """Resource is available when prior assignment is marked returned."""
        ResourceAssignment.objects.create(
            resource=self.res_ts1, target=self.section, returned=True,
        )
        available = self.program.getAvailableResources(self.timeslot2)
        available_names = [r.name for r in available]
        self.assertIn('Projector #1', available_names)

    def test_unavailable_when_prior_assignment_not_returned(self):
        """Resource is NOT available when prior assignment is not returned."""
        ResourceAssignment.objects.create(
            resource=self.res_ts1, target=self.section, returned=False,
        )
        available = self.program.getAvailableResources(self.timeslot2)
        available_names = [r.name for r in available]
        self.assertNotIn('Projector #1', available_names)

    def test_current_timeslot_taken_still_unavailable(self):
        """Resource with assignment in current timeslot is unavailable."""
        ResourceAssignment.objects.create(
            resource=self.res_ts2, target=self.section,
        )
        available = self.program.getAvailableResources(self.timeslot2)
        available_names = [r.name for r in available]
        self.assertNotIn('Projector #1', available_names)

    def test_has_unreturned_prior_assignment(self):
        """Test the per-resource helper method."""
        ra = ResourceAssignment.objects.create(
            resource=self.res_ts1, target=self.section, returned=False,
        )
        self.assertTrue(self.res_ts2.has_unreturned_prior_assignment(self.timeslot2))
        ra.returned = True
        ra.save()
        self.assertFalse(self.res_ts2.has_unreturned_prior_assignment(self.timeslot2))
