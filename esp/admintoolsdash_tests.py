"""
Tests for admintoolsdash.py — CustomIndexDashboard and CustomAppIndexDashboard.
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase, RequestFactory

from admintoolsdash import CustomIndexDashboard, CustomAppIndexDashboard


class CustomIndexDashboardTest(TestCase):

    def _make_context(self, models=None):
        """Build a minimal context dict that init_with_context expects."""
        request = RequestFactory().get('/admin/')
        request.user = MagicMock()

        if models is None:
            models = []

        context = {
            'request': request,
        }
        return context, models

    @patch('admintoolsdash.get_admin_site_name', return_value='admin')
    @patch('admintoolsdash.get_avail_models', return_value=[])
    def test_init_creates_quick_links(self, mock_avail, mock_site_name):
        context, _ = self._make_context()
        dashboard = CustomIndexDashboard()
        dashboard.init_with_context(context)

        titles = [child.title for child in dashboard.children]
        self.assertIn('Quick links', titles)

    @patch('admintoolsdash.get_admin_site_name', return_value='admin')
    @patch('admintoolsdash.get_avail_models', return_value=[])
    def test_init_creates_recent_actions(self, mock_avail, mock_site_name):
        context, _ = self._make_context()
        dashboard = CustomIndexDashboard()
        dashboard.init_with_context(context)

        from admin_tools.dashboard import modules
        recent = [c for c in dashboard.children if isinstance(c, modules.RecentActions)]
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0].limit, 10)

    @patch('admintoolsdash.get_admin_site_name', return_value='admin')
    @patch('admintoolsdash.get_avail_models')
    def test_models_grouped_by_app(self, mock_avail, mock_site_name):
        """Models from the same app should be in one ModelList panel."""
        from django.apps import apps as django_apps

        FakeModel = MagicMock()
        FakeModel._meta.app_label = 'esp'
        FakeModel.__module__ = 'esp.users.models'
        FakeModel.__name__ = 'ESPUser'

        mock_avail.return_value = [(FakeModel, {})]

        with patch.object(django_apps, 'get_app_config') as mock_cfg:
            mock_cfg.return_value.verbose_name = 'ESP'
            context, _ = self._make_context()
            dashboard = CustomIndexDashboard()
            dashboard.init_with_context(context)

        from admin_tools.dashboard import modules
        model_lists = [c for c in dashboard.children if isinstance(c, modules.ModelList)]
        self.assertEqual(len(model_lists), 1)
        self.assertIn('esp.users.models.ESPUser', model_lists[0].models)

    @patch('admintoolsdash.get_admin_site_name', return_value='admin')
    @patch('admintoolsdash.get_avail_models')
    def test_multiple_apps_get_separate_panels(self, mock_avail, mock_site_name):
        from django.apps import apps as django_apps

        def make_model(app_label, module, name):
            m = MagicMock()
            m._meta.app_label = app_label
            m.__module__ = module
            m.__name__ = name
            return m

        mock_avail.return_value = [
            (make_model('esp', 'esp.users.models', 'ESPUser'), {}),
            (make_model('program', 'esp.program.models', 'Program'), {}),
        ]

        def cfg(label):
            c = MagicMock()
            c.verbose_name = label.capitalize()
            return c

        with patch.object(django_apps, 'get_app_config', side_effect=cfg):
            context, _ = self._make_context()
            dashboard = CustomIndexDashboard()
            dashboard.init_with_context(context)

        from admin_tools.dashboard import modules
        model_lists = [c for c in dashboard.children if isinstance(c, modules.ModelList)]
        self.assertEqual(len(model_lists), 2)


class CustomAppIndexDashboardTest(TestCase):

    def _make_dashboard(self, app_title='ESP', models=None):
        if models is None:
            models = ['esp.users.models.ESPUser']
        dashboard = CustomAppIndexDashboard(
            app_title=app_title,
            models=models,
        )
        return dashboard

    def test_title_is_empty(self):
        dashboard = self._make_dashboard()
        self.assertEqual(dashboard.title, '')

    def test_has_model_list(self):
        from admin_tools.dashboard import modules
        dashboard = self._make_dashboard()
        model_lists = [c for c in dashboard.children if isinstance(c, modules.ModelList)]
        self.assertEqual(len(model_lists), 1)

    def test_recent_actions_filtered_to_app_models(self):
        from admin_tools.dashboard import modules
        models = ['esp.users.models.ESPUser']
        dashboard = self._make_dashboard(models=models)
        recent = [c for c in dashboard.children if isinstance(c, modules.RecentActions)]
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0].include_list, models)

    def test_recent_actions_limit(self):
        from admin_tools.dashboard import modules
        dashboard = self._make_dashboard()
        recent = [c for c in dashboard.children if isinstance(c, modules.RecentActions)]
        self.assertEqual(recent[0].limit, 10)

    def test_init_with_context_calls_super(self):
        dashboard = self._make_dashboard()
        request = RequestFactory().get('/admin/')
        context = MagicMock()
        context.__getitem__ = MagicMock(return_value=request)
        # Should not raise
        dashboard.init_with_context(context)
