import os
import tempfile

from django.core.management import call_command
from django.core.management.base import CommandError

from esp.tests.util import CacheFlushTestCase as TestCase
from esp.users.models import K12School


class ImportNcesSchoolsCommandTest(TestCase):
    def _write_csv(self, content):
        fd, path = tempfile.mkstemp(suffix='.csv')
        os.close(fd)
        with open(path, 'w', encoding='utf-8', newline='') as f:
            f.write(content)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        return path

    def test_raises_on_missing_file(self):
        with self.assertRaises(CommandError):
            call_command('import_nces_schools', csv='does-not-exist.csv')

    def test_raises_on_missing_required_column(self):
        path = self._write_csv("SCH_NAME,LCITY\nSpringfield Academy,Springfield\n")
        with self.assertRaises(CommandError):
            call_command('import_nces_schools', csv=path)

    def test_creates_school_and_normalizes_state(self):
        path = self._write_csv(
            "SCH_NAME,LCITY,LSTATE,NCESSCH\n"
            "Springfield Academy,Springfield,ma,123\n"
        )
        call_command('import_nces_schools', csv=path)
        school = K12School.objects.get(school_id='123')
        self.assertEqual(school.name, 'Springfield Academy')
        self.assertEqual(school.city, 'Springfield')
        self.assertEqual(school.state, 'MA')

    def test_updates_existing_school_and_sets_school_id(self):
        # Existing record with no NCES id; should match on name+state and get school_id populated.
        K12School.objects.create(name='Springfield Academy', city='Old City', state='MA')
        path = self._write_csv(
            "SCH_NAME,LCITY,LSTATE,NCESSCH\n"
            "Springfield Academy,Springfield,MA,999\n"
        )
        call_command('import_nces_schools', csv=path)
        school = K12School.objects.get(name='Springfield Academy')
        self.assertEqual(school.city, 'Springfield')
        self.assertEqual(school.state, 'MA')
        self.assertEqual(school.school_id, '999')

    def test_dry_run_makes_no_changes(self):
        path = self._write_csv(
            "SCH_NAME,LCITY,LSTATE,NCESSCH\n"
            "Springfield Academy,Springfield,MA,123\n"
        )
        call_command('import_nces_schools', csv=path, dry_run=True)
        self.assertEqual(K12School.objects.count(), 0)

