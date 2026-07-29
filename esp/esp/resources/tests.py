from __future__ import absolute_import
from datetime import datetime

from django.db.models import ProtectedError
from django.test import SimpleTestCase

from esp.cal.models import Event, EventType
from esp.program.models import Program
from esp.program.models.class_ import ClassSubject, ClassSection, ClassCategories
from esp.resources.models import Resource, ResourceType, ResourceRequest
from esp.tests.util import CacheFlushTestCase as TestCase


class MitBuildingNumTest(SimpleTestCase):
    def testParsing(self):
        cases = {
            '13-1143':    '13',   # pure-number building
            'W20-401':    'W20',  # letter-prefixed
            '6C-120':     '6C',   # digit+letter
            '14N-132':    '14N',
            '  13-1143 ': '13',   # surrounding whitespace stripped
            'Lobby 10':   '',     # space in candidate -> not a building number
            'TBA':        '',     # no digit
            '':           '',     # empty
            'TOOLONG-1':  '',     # > 6 chars
            'AB!-1':      '',     # non-alphanumeric char
        }
        for name, expected in cases.items():
            self.assertEqual(Resource(name=name).mit_building_num, expected,
                             msg='name={!r}'.format(name))

    def testWhereisUrl(self):
        self.assertEqual(Resource(name='13-1143').mit_whereis_url,
                         'https://whereis.mit.edu/?go=13')
        self.assertEqual(Resource(name='W20-401').mit_whereis_url,
                         'https://whereis.mit.edu/?go=W20')
        self.assertEqual(Resource(name='TBA').mit_whereis_url,
                         'https://whereis.mit.edu/')

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
