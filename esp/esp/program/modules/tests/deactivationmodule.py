from __future__ import absolute_import

from django.db.models import Q

from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser, PersistentQueryFilter


class DeactivationModuleTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        super(DeactivationModuleTest, self).setUp(*args, **kwargs)

        self.admin = self.admins[0]
        self.admin.set_password('password')
        self.admin.save()
        self.client.login(username=self.admin.username, password='password')

        # Sanity check that the module is present.
        self.assertTrue(self.program.hasModule('DeactivationModule'))

    def _deactivatefinal_url(self):
        return '/manage/%s/deactivatefinal' % self.program.url

    def test_deactivatefinal_rejects_non_post_or_missing_filterid(self):
        response = self.client.get(self._deactivatefinal_url())
        self.assertEqual(response.status_code, 500)
        self.assertContains(response, 'Filter has not been properly set', status_code=500)

        # Post without filterid still fails
        response = self.client.post(self._deactivatefinal_url(), {'confirm': 'true'})
        self.assertEqual(response.status_code, 500)
        self.assertContains(response, 'Filter has not been properly set', status_code=500)

    def test_deactivatefinal_rejects_missing_confirmation(self):
        q = Q(id__in=[self.students[0].id])
        filter_obj = PersistentQueryFilter.create_from_Q(ESPUser, q)
        filter_obj.save()

        response = self.client.post(self._deactivatefinal_url() + '?filterid=%s' % filter_obj.id, {})
        self.assertEqual(response.status_code, 500)
        self.assertContains(response, 'You must confirm that you want to deactivate these users.', status_code=500)

    def test_deactivatefinal_handles_empty_filter_query(self):
        q = Q(id__in=[])
        filter_obj = PersistentQueryFilter.create_from_Q(ESPUser, q)
        filter_obj.save()

        response = self.client.post(self._deactivatefinal_url() + '?filterid=%s' % filter_obj.id, {'confirm': 'true'})
        self.assertEqual(response.status_code, 500)
        self.assertContains(response, 'Your query did not match any users', status_code=500)

    def test_deactivatefinal_deactivates_filtered_users(self):
        # choose a couple of students
        targets = self.students[:2]
        active_ids = [u.id for u in targets]
        for u in targets:
            self.assertTrue(u.is_active)

        q = Q(id__in=active_ids)
        filter_obj = PersistentQueryFilter.create_from_Q(ESPUser, q)
        filter_obj.save()

        response = self.client.post(self._deactivatefinal_url() + '?filterid=%s' % filter_obj.id, {'confirm': 'true'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Congratulations! 2 users were deactivated!', status_code=200)

        deactivated = ESPUser.objects.filter(id__in=active_ids)
        self.assertEqual(deactivated.filter(is_active=False).count(), 2)

        # preserve other users
        remaining = ESPUser.objects.exclude(id__in=active_ids)
        self.assertTrue(remaining.filter(is_active=True).exists())
