from datetime import datetime

from django.db.models import ProtectedError

from esp.cal.models import Event, EventType
from esp.program.models import Program
from esp.program.models.class_ import ClassSubject, ClassSection, ClassCategories
from esp.resources.models import Resource, ResourceType, ResourceRequest
from esp.tests.util import CacheFlushTestCase as TestCase

class ResourceTypeTest(TestCase):

    def setUp(self):
        super(ResourceTypeTest, self).setUp()
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
