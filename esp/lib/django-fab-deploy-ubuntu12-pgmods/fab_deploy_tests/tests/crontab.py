from __future__ import absolute_import
from fabtest import fab
from fab_deploy import crontab
from .base import FabDeployTest

class CrontabTest(FabDeployTest):
    snapshot = 'fabtest-prepared-server'

    def current(self):
        return fab(crontab.get_content)

    def add(self, content, marker):
        return fab(crontab.add_line, content, marker)

    def remove(self, marker):
        return fab(crontab.remove_line, marker)

    def update(self, content, marker):
        return fab(crontab.update_line, content, marker)

    def test_crontab(self):
        line1 = '@reboot echo 123'
        line2 = '@reboot echo 345'
        new_line2 = '@reboot echo 567'

        self.add(line1, 'line1')
        self.add(line2, 'line2')
        current = self.current()

        self.assertTrue(line1 in current)
        self.assertTrue(line2 in current)
        self.assertFalse(new_line2 in current)

        self.update(new_line2, 'line2')
        current = self.current()

        self.assertTrue(line1 in current)
        self.assertFalse(line2 in current)
        self.assertTrue(new_line2 in current)

        self.remove('line1')
        current = self.current()

        self.assertFalse(line1 in current)
        self.assertFalse(line2 in current)
        self.assertTrue(new_line2 in current)

        fab(crontab.puts_content)
